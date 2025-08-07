# GCP GKE Deployment for Log Analyzer

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "container_api" {
  service = "container.googleapis.com"
}

resource "google_project_service" "compute_api" {
  service = "compute.googleapis.com"
}

# VPC Network
resource "google_compute_network" "log_analyzer_vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.compute_api]
}

# Subnet
resource "google_compute_subnetwork" "log_analyzer_subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.log_analyzer_vpc.id

  secondary_ip_range {
    range_name    = "k8s-pod-range"
    ip_cidr_range = var.pod_cidr
  }

  secondary_ip_range {
    range_name    = "k8s-service-range"
    ip_cidr_range = var.service_cidr
  }
}

# Service Account for GKE nodes
resource "google_service_account" "gke_service_account" {
  account_id   = "${var.cluster_name}-sa"
  display_name = "GKE Service Account for ${var.cluster_name}"
}

resource "google_project_iam_member" "gke_service_account_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
    "roles/container.nodeServiceAccount"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

# GKE Cluster
resource "google_container_cluster" "log_analyzer" {
  name     = var.cluster_name
  location = var.region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.log_analyzer_vpc.name
  subnetwork = google_compute_subnetwork.log_analyzer_subnet.name

  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable Network Policy
  network_policy {
    enabled = true
  }

  # Enable IP Alias
  ip_allocation_policy {
    cluster_secondary_range_name  = "k8s-pod-range"
    services_secondary_range_name = "k8s-service-range"
  }

  # Logging and Monitoring
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Master Auth
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  # Addons
  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    
    http_load_balancing {
      disabled = false
    }

    network_policy_config {
      disabled = false
    }
  }

  # Maintenance window
  maintenance_policy {
    recurring_window {
      start_time = "2023-01-01T01:00:00Z"
      end_time   = "2023-01-01T05:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA"
    }
  }

  depends_on = [
    google_project_service.container_api,
    google_compute_network.log_analyzer_vpc,
    google_compute_subnetwork.log_analyzer_subnet
  ]
}

# Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.log_analyzer.name
  node_count = var.initial_node_count

  # Autoscaling
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  # Node configuration
  node_config {
    preemptible  = var.preemptible
    machine_type = var.machine_type

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      env = var.environment
    }

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    tags = ["gke-node", "${var.cluster_name}-gke"]
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  # Node management
  management {
    auto_repair  = true
    auto_upgrade = true
  }

  # Update strategy
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# Container Registry
resource "google_container_registry" "registry" {
  project  = var.project_id
  location = "US"
}

# IAM binding for Container Registry
resource "google_storage_bucket_iam_member" "viewer" {
  bucket = google_container_registry.registry.id
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.gke_service_account.email}"
}

# Firewall rule for health checks
resource "google_compute_firewall" "allow_health_check" {
  name    = "${var.cluster_name}-allow-health-check"
  network = google_compute_network.log_analyzer_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8080", "5000"]
  }

  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["gke-node"]
}