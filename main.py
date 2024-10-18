import re
import json
from collections import defaultdict
import os
from typing import Dict, List, Any

# Constants for DNS configuration
ZONE_FILE = "zone.txt"
HIGH_LEVEL_DOMAIN = "example.com"
DOMAIN_NAME = "internal.example.com"
SOA_NS_ENTRY = "mstbind.example.com"
SOA_HOSTMASTER_ENTRY = "hostmaster.example.com."
HOST_IPV4 = "192.168.0.0."

# Ensure necessary directories exist
for dir in ["forward_zone", "reverse_zone", "json"]:
    os.makedirs(dir, exist_ok=True)

def parse_record(line: str) -> Dict[str, Any]:
    """
    Parse a single DNS record line and return a dictionary of its components.
    """
    parts = line.strip().split(':', 1)
    record_type = parts[0].strip()
    details = parts[1].strip() if len(parts) > 1 else ""
    
    record = {"type": record_type}
    
    # Handle specific record types
    if record_type in ["SOA", "NS", "CNAME"]:
        record["domain"] = details.split()[0]
    elif record_type == "A":
        record["ip"] = details.split()[0]
    
    # Parse additional parameters
    record.update(dict(re.findall(r'(\w+)=([^,\s]+)', details)))
    
    return record

def parse_file(file_path: str) -> Dict[str, Any]:
    """
    Parse the entire DNS zone file and return a structured dictionary of its contents.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    dns_data = {}
    current_name = None

    for line in lines:
        line = line.strip()
        if line.startswith("Name="):
            # Parse the Name, Records, and Children fields
            name, records, children = [part.split('=')[1] for part in line.split(',')]
            name = name or "root"
            dns_data[name] = {
                "Records": int(records),
                "Children": int(children),
                "DNS_Records": []
            }
            current_name = name
        elif line and current_name:
            dns_data[current_name]["DNS_Records"].append(parse_record(line))

    return dns_data

def generate_bind9_zone(json_data: Dict[str, Any], zone_name: str, output_file: str):
    """
    Generate a BIND9 zone file from the parsed JSON data.
    """
    with open(output_file, 'w') as f:
        # Write SOA record
        soa = next(r for r in json_data['root']['DNS_Records'] if r['type'] == 'SOA')
        f.write(f"$TTL {soa['ttl'].strip(')')}\n")
        f.write(f"@ IN SOA {SOA_NS_ENTRY}. {SOA_HOSTMASTER_ENTRY} (\n")
        for field in ['serial', 'refresh', 'retry', 'expire', 'minttl']:
            f.write(f"\t{soa[field]}\t; {field.capitalize()}\n")
        f.write(")\n\n")

        # Add NS record for mstbind to every forward zone
        f.write(f"@\tIN\tNS\t{SOA_NS_ENTRY}.\n\n")

        # Add A record for mstbind only if the zone matches
        if zone_name.endswith(HIGH_LEVEL_DOMAIN):
            f.write(f"{SOA_NS_ENTRY}.\tIN\tA\t{HOST_IPV4}\n\n")

        # Write NS records
        for record in json_data['root']['DNS_Records']:
            if record['type'] == 'NS':
                f.write(f"@\t{record['ttl'].strip(')')}\tIN NS\t{record['domain']}\n")
        f.write("\n")

        # Group A and CNAME records
        a_records = defaultdict(list)
        cname_records = defaultdict(list)

        for domain, data in json_data.items():
            if domain != 'root':
                for record in data['DNS_Records']:
                    if record['type'] == 'A':
                        a_records[record['ttl'].strip(')')].append((domain, record['ip']))
                    elif record['type'] == 'CNAME':
                        cname_records[record['ttl'].strip(')')].append((domain, record['domain']))

        write_grouped_records(f, "A", a_records)
        write_grouped_records(f, "CNAME", cname_records)

def write_grouped_records(file, record_type: str, records: Dict[str, List[tuple]]):
    """
    Write grouped DNS records (A or CNAME) to the zone file.
    """
    file.write(f"; {record_type} Records\n")
    for ttl, record_list in records.items():
        file.write(f"; TTL {ttl}\n")
        for domain, value in record_list:
            file.write(f"{domain}\t{ttl}\tIN {record_type}\t{value}\n")
        file.write("\n")

def generate_reverse_zone(json_data: Dict[str, Any], reverse_zones: Dict[str, List[tuple]]):
    """
    Generate reverse zone entries from the parsed JSON data.
    """
    for domain, data in json_data.items():
        if domain != 'root':
            for record in data['DNS_Records']:
                if record['type'] == 'A':
                    ip_parts = record['ip'].split('.')
                    reversed_ip = '.'.join(reversed(ip_parts))
                    subnet = '.'.join(ip_parts[:3])
                    # Use setdefault to simplify the dictionary update
                    reverse_zones.setdefault(subnet, []).append((reversed_ip, domain))

def write_reverse_zone_files(reverse_zones: Dict[str, List[tuple]]):
    """
    Write reverse zone files for each subnet.
    """
    mstbind_subnet = '.'.join(HOST_IPV4.split('.')[:3])
    reversed_host_ipv4 = '.'.join(reversed(HOST_IPV4.split('.')))

    for subnet, records in reverse_zones.items():
        reverse_file = f"reverse_zone/db.{subnet}.arpa"
        with open(reverse_file, 'w') as f:
            write_reverse_zone_header(f)
            for reversed_ip, domain in records:
                first_octet = reversed_ip.split('.')[0]
                f.write(f"{first_octet}\tIN\tPTR\t{domain}.{DOMAIN_NAME}.\n")

            # Add reverse zone entry for mstbind if in the same subnet
            if subnet == mstbind_subnet:
                f.write(f"{reversed_host_ipv4.split('.')[0]}\tIN\tPTR\t{SOA_NS_ENTRY}.\n")

def write_reverse_zone_header(file):
    """
    Write the header for a reverse zone file.
    """
    file.write(f"$TTL 86400\n")
    file.write(f"@ IN SOA {SOA_NS_ENTRY}. {SOA_HOSTMASTER_ENTRY} (\n")
    file.write(f"\t1 ; Serial\n")
    file.write(f"\t604800 ; Refresh\n")
    file.write(f"\t86400 ; Retry\n")
    file.write(f"\t2419200 ; Expire\n")
    file.write(f"\t86400 ; Minimum TTL\n")
    file.write(")\n\n")
    file.write(f"@ IN NS {SOA_NS_ENTRY}.\n\n")

def generate_bind9_config(input_file: str, output_file: str, reverse_zones: Dict[str, List[tuple]]):
    """
    Generate the main BIND9 configuration file.
    """
    with open(input_file, 'r') as f:
        zones = [line.strip() for line in f if line.strip()]

    with open(output_file, 'w') as f:
        f.write("// BIND configuration file\n")
        f.write("    // Place additional options here.\n\n\n")
        # Write forward zone configurations
        for zone in zones:
            write_zone_config(f, zone, "forward_zone")

        # Write reverse zone configurations
        for subnet in reverse_zones:
            reversed_subnet = '.'.join(reversed(subnet.split('.')))
            reverse_zone = f"{reversed_subnet}.in-addr.arpa"
            write_zone_config(f, reverse_zone, "reverse_zone", f"db.{subnet}.arpa")

    print(f"BIND configuration file has been generated: {output_file}")

def write_zone_config(file, zone: str, zone_type: str, db_file: str = None):
    """
    Write a single zone configuration block.
    """
    file.write(f'zone "{zone}" in {{\n')
    file.write("    type master;\n")
    file.write(f'    file "/etc/bind/{zone_type}/{db_file or f"db.{zone}"}";')
    file.write("\n};\n\n")

def main():
    """
    Main function to orchestrate the DNS zone file generation process.
    """
    reverse_zones = {}

    # Read the list of zones from the zone file
    with open(ZONE_FILE, 'r') as file:
        zones = [line.strip() for line in file if line.strip()]

    for zone in zones:
        file_path = f"zone_query/{zone}.txt"
        dns_json = parse_file(file_path)
        
        # Write JSON output for debugging or further processing
        with open(f"json/{zone}.json", 'w') as json_file:
            json.dump(dns_json, json_file, indent=2)
        
        # Generate forward zone file
        generate_bind9_zone(dns_json, zone, f"forward_zone/db.{zone}")
        
        # Collect reverse zone information
        generate_reverse_zone(dns_json, reverse_zones)

    # Write reverse zone files
    write_reverse_zone_files(reverse_zones)
    
    # Generate main BIND9 configuration file
    generate_bind9_config(ZONE_FILE, "named.conf.local", reverse_zones)

if __name__ == "__main__":
    main()