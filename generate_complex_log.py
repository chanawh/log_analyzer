import random
from datetime import datetime, timedelta

hosts = [f"NAS110-{i}(id{i})" for i in range(1, 7)]
programs = [
    "/boot/kernel.amd64/kernel",
    "isi_papi_d",
    "isi_stats_d",
    "isi_healthcheck:check:smartconnect_sip_responsive.pyc",
    "isi_healthcheck:check:admin_homedir_shared.pyc",
    "syslogd",
    "sshd",
    "ntpq",
]
levels_priorities = ["<0.6>", "<1.3>", "<1.4>", "<3.3>", "<3.4>", "<4.3>"]
log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]  # Add these tags to each line
actions = [
    "route_output: can't delete ARP entries from BE interface mlxen1",
    "last message repeated {} times",
    "getpwuid failed:0 user_id: {}",
    "Timeout while running '/sbin/ping -t 1 -c 1 -i 0.1 {}'",
    "error: kex_exchange_identification: Connection closed by remote host",
    "NTP FIPS mode is disabled",
    "Two manager processes for job {}",
    "Successfully sent to ['{}'] through '{}'",
    "Skipping orphan SID SID:{} with shell privileges",
    "Skipping orphan SID UID:{} with shell privileges",
]
user_ids = [903, 179, 901, 4030, 4294967295, 103, 2005]
jobs = [39354, 12345, 67890]
# Updated to clearly fake/test values
emails = ["user1@example.com", "user2@example.com"]
mailrelays = ["mailrelay.example.com", "relay01.test.local"]
sid_template = "SID:S-1-5-21-{}-{}-{}-{}"
uids = [2005, 3001, 4002, 5003]

# Span across multiple dates
start_date = datetime(2023, 11, 28, 0, 0, 0)
end_date = datetime(2023, 12, 4, 23, 59, 59)
lines = []

dt = start_date
while dt <= end_date:
    for hour in range(0, 24):
        for minute in range(0, 60, random.choice([10, 15, 30])):
            current_dt = dt.replace(
                hour=hour, minute=minute, second=random.randint(0, 59)
            )
            dtstr = current_dt.strftime(
                "%Y-%m-%dT%H:%M:%S.{:06d}+01:00".format(random.randint(0, 999999))
            )
            host = random.choice(hosts)
            prio = random.choice(levels_priorities)
            program = random.choice(programs)
            log_level = random.choice(log_levels)
            line = ""
            if program == "syslogd":
                action = actions[1].format(random.choice([1, 2, 3, 4]))
                line = f"{dtstr} {prio} {host.split('(')[0]} syslogd: {action} [{log_level}]"
            elif program == "isi_papi_d":
                action = actions[2].format(random.choice(user_ids))
                pid = random.randint(100, 99999)
                line = (
                    f"{dtstr} {prio} {host} isi_papi_d[{pid}]: {action} [{log_level}]"
                )
            elif program == "/boot/kernel.amd64/kernel":
                iface = random.choice(["mlxen1", "mlxen0"])
                line = f"{dtstr} {prio} {host} /boot/kernel.amd64/kernel: route_output: can't delete ARP entries from BE interface {iface} [{log_level}]"
            elif program == "isi_healthcheck:check:smartconnect_sip_responsive.pyc":
                ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
                pid = random.randint(100, 99999)
                line = f"{dtstr} {prio} {host} isi_healthcheck:check:smartconnect_sip_responsive.pyc[{pid}]: Timeout while running '/sbin/ping -t 1 -c 1 -i 0.1 {ip}'. [{log_level}]"
            elif program == "isi_healthcheck:check:admin_homedir_shared.pyc":
                pid = random.randint(100, 99999)
                sid = sid_template.format(
                    random.randint(1000000000, 9999999999),
                    random.randint(100000000, 999999999),
                    random.randint(100000000, 999999999),
                    random.randint(10000, 99999),
                )
                line = f"{dtstr} {prio} {host} isi_healthcheck:check:admin_homedir_shared.pyc[{pid}]: Skipping orphan SID {sid} with shell privileges [{log_level}]"
            elif program == "sshd":
                pid = random.randint(100, 99999)
                line = f"{dtstr} {prio} {host} sshd[{pid}]: error: kex_exchange_identification: Connection closed by remote host [{log_level}]"
            elif program == "isi_stats_d":
                pid = random.randint(100, 99999)
                job = random.choice(jobs)
                line = f"{dtstr} {prio} {host} isi_stats_d[{pid}]: Two manager processes for job {job} [{log_level}]"
            elif program == "ntpq":
                pid = random.randint(100, 99999)
                line = f"{dtstr} {prio} {host} ntpq[{pid}]: NTP FIPS mode is disabled [{log_level}]"
            else:
                line = f"{dtstr} {prio} {host} {program}: Unknown event [{log_level}]"
            lines.append(line)
    dt += timedelta(days=1)

# Add some success mail and orphan UID events
for i in range(30):  # More events, more dates
    dt = start_date + timedelta(
        days=random.randint(0, (end_date - start_date).days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    dtstr = dt.strftime(
        "%Y-%m-%dT%H:%M:%S.{:06d}+01:00".format(random.randint(0, 999999))
    )
    host = random.choice(hosts)
    prio = "<1.4>"
    pid = random.randint(100, 99999)
    email = random.choice(emails)
    relay = random.choice(mailrelays)
    log_level = random.choice(log_levels)
    line = f"{dtstr} {prio} {host} /isi_celog_alerting[{pid}]: Successfully sent to ['{email}'] through '{relay}' [{log_level}]"
    lines.append(line)
    # Orphan UID
    uid = random.choice(uids)
    line2 = f"{dtstr} {prio} {host} isi_healthcheck:check:admin_homedir_shared.pyc[{pid}]: Skipping orphan SID UID:{uid} with shell privileges [{log_level}]"
    lines.append(line2)

with open("test_complex.log", "w") as f:
    f.write("\n".join(lines))
print("Generated test_complex.log with", len(lines), "lines.")
