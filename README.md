# DNS Zone Generator

## Overview

This Python script generates BIND9 compatible zone files and configurations from a given set of DNS records. It parses input files containing DNS record information, generates forward and reverse zone files, and creates a main BIND9 configuration file.

## Features

- Parses DNS record information from input files
- Generates forward zone files for each specified domain
- Creates reverse zone files for IP subnets
- Produces a main BIND9 configuration file
- Outputs JSON files for each parsed zone (useful for debugging or further processing)

## Requirements

- Python 3.6+
- No external libraries required (uses only Python standard library)

## Usage

1. Prepare your input files:
   - Create a `zone.txt` file listing all the domains you want to generate zone files for, one per line.
   - For each domain listed in `zone.txt`, create a corresponding file in the `zone_query/` directory (e.g., `zone_query/example.com.txt`) containing the DNS records for that domain.

2. Run the script:
   ```
   python dns_zone_generator.py
   ```

3. The script will generate the following outputs:
   - Forward zone files in the `forward_zone/` directory
   - Reverse zone files in the `reverse_zone/` directory
   - JSON representations of parsed data in the `json/` directory
   - A main BIND9 configuration file named `named.conf.local`

## Configuration

You can modify the following constants at the top of the script to match your setup:

- `ZONE_FILE`: The name of the file containing the list of zones to process (default: "zone.txt")
- `HIGH_LEVEL_DOMAIN`: The top-level domain for your DNS setup (default: "example.com")
- `DOMAIN_NAME`: The internal domain name (default: "internal.example.com")
- `SOA_NS_ENTRY`: The authoritative name server for your zones (default: "mstbind.example.com")
- `SOA_HOSTMASTER_ENTRY`: The email address for the hostmaster (default: "hostmaster.example.com.")
- `HOST_IPV4`: The IPv4 address for the authoritative name server (default: "192.168.0.0.")

## Input File Format

### zone.txt
```
example.com
subdomain.example.com
```

### zone_query/example.com.txt
```
Name=,Records=5,Children=2
SOA:example.com ttl=86400)
NS:ns1.example.com ttl=86400)
NS:ns2.example.com ttl=86400)
A:192.168.1.1 ttl=3600)
CNAME:www.example.com ttl=3600)
```

## Output

The script generates the following types of files:

1. Forward zone files (e.g., `forward_zone/db.example.com`)
2. Reverse zone files (e.g., `reverse_zone/db.192.168.1.arpa`)
3. JSON files containing parsed data (e.g., `json/example.com.json`)
4. A main BIND9 configuration file (`named.conf.local`)

## Functions

- `parse_record()`: Parses a single DNS record line
- `parse_file()`: Parses an entire DNS zone file
- `generate_bind9_zone()`: Generates a BIND9 zone file from parsed data
- `generate_reverse_zone()`: Generates reverse zone entries
- `write_reverse_zone_files()`: Writes reverse zone files
- `generate_bind9_config()`: Generates the main BIND9 configuration file
- `main()`: Orchestrates the entire zone generation process




