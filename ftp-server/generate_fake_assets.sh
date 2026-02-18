#!/bin/bash
set -e

echo "================================================"
echo "Generating Fake FTP Assets for Honeypot"
echo "================================================"

# Directory structure
echo "Creating directory structure..."
mkdir -p ftp-data/guest
mkdir -p ftp-data/prof1/{MoUs,research,datasets}
mkdir -p ftp-data/prof2/{MoUs,research,datasets}

# Install required tools if not present
if ! command -v enscript &> /dev/null; then
    echo "Installing enscript and ghostscript..."
    sudo apt-get update
    sudo apt-get install -y enscript ghostscript
fi

# Generate fake MoUs (PDFs) - 7 for each professor
echo ""
echo "Generating fake MoU documents..."
MINISTRIES=("Health and Family Welfare" "Science and Technology" "Home Affairs" "External Affairs" "Defense" "Education" "Electronics and IT")

for i in {0..6}; do
    MINISTRY="${MINISTRIES[$i]}"
    cat > /tmp/mou_temp.txt <<EOF
MEMORANDUM OF UNDERSTANDING

Between

Ministry of ${MINISTRY}
Government of India

and

Pandemic Studies & Risk Surveillance Center (PSRSC)
Indian Institute of Technology Kanpur

Date: $(date +%Y-%m-%d)

CLASSIFIED - RESTRICTED DISTRIBUTION

This MoU establishes collaboration on pandemic risk assessment,
early warning systems, and coordinated response mechanisms.

Project Code: GOI-PSRSC-${RANDOM}
Clearance Level: SECRET
Duration: 3 years

Authorized Signatories:
- Secretary, Ministry of ${MINISTRY}
- Director, PSRSC, IIT Kanpur

[CONFIDENTIAL ANNEXURES ATTACHED]
EOF
    
    enscript -B -f Courier10 -o - /tmp/mou_temp.txt | ps2pdf - "ftp-data/prof1/MoUs/MoU_${MINISTRY// /_}_$(date +%Y).pdf"
    cp "ftp-data/prof1/MoUs/MoU_${MINISTRY// /_}_$(date +%Y).pdf" "ftp-data/prof2/MoUs/"
    echo "  ✓ Created MoU with Ministry of ${MINISTRY}"
done

# Generate fake research papers (PDFs) - 12 for each professor
echo ""
echo "Generating fake research papers..."
TOPICS=(
    "COVID-19 Transmission Dynamics in High-Density Urban Areas"
    "Predictive Modeling of Pandemic Spread Using AI/ML"
    "Vaccine Distribution Optimization for Indian Population"
    "Economic Impact Assessment of Pandemic Lockdowns"
    "Mental Health Crisis Management During Pandemics"
    "Supply Chain Resilience for Medical Equipment"
    "Genomic Surveillance of Emerging Viral Variants"
    "Contact Tracing Technology and Privacy Concerns"
    "Hospital Capacity Planning for Pandemic Surges"
    "Risk Communication Strategies in Public Health"
    "Cross-Border Pandemic Response Coordination"
    "Long-term Health Effects of COVID-19 Survivors"
)

for i in {0..11}; do
    TOPIC="${TOPICS[$i]}"
    cat > /tmp/research_temp.txt <<EOF
CLASSIFIED RESEARCH PAPER - DO NOT DISTRIBUTE

Title: ${TOPIC}

Authors:
- Prof. Rajesh Kumar, PSRSC, IIT Kanpur
- Dr. Priya Sharma, Ministry of Health
- Dr. Amit Verma, ICMR

Date: $(date +%Y-%m-%d)
Classification: RESTRICTED
Project ID: PSRSC-RP-${RANDOM}

ABSTRACT
This study examines critical aspects of pandemic response
specific to Indian demographic and geographic conditions.
Findings indicate [REDACTED] with implications for
national security and public health policy.

KEYWORDS: pandemic, India, risk assessment, modeling

[FULL PAPER - 45 PAGES - AVAILABLE TO AUTHORIZED PERSONNEL ONLY]

Contact: research@psrsc.iitk.ac.in
Clearance Required: GOI-SECRET-${RANDOM}
EOF
    
    enscript -B -f Courier9 -o - /tmp/research_temp.txt | ps2pdf - "ftp-data/prof1/research/RP_$(echo $TOPIC | cut -d' ' -f1-3 | tr ' ' '_').pdf"
    cp "ftp-data/prof1/research/RP_$(echo $TOPIC | cut -d' ' -f1-3 | tr ' ' '_').pdf" "ftp-data/prof2/research/"
    echo "  ✓ Created research paper: ${TOPIC:0:50}..."
done

# Generate fake datasets (CSV) - 5 for each professor
echo ""
echo "Generating fake pandemic datasets..."
DATASET_NAMES=("COVID_Cases_India_2020" "Vaccination_Progress_2021" "Hospital_Capacity_Utilization" "Mortality_Analysis_Urban" "Contact_Tracing_Network")

for i in {0..4}; do
    DATASET="${DATASET_NAMES[$i]}"
    echo "date,region,cases,deaths,recovered,active,testing_rate" > "ftp-data/prof1/datasets/${DATASET}.csv"
    
    # Generate 365 days of fake data
    for d in {1..365}; do
        DATE=$(date -d "2020-01-01 +$d days" +%Y-%m-%d)
        REGION=$((RANDOM % 28 + 1))  # 28 states
        CASES=$((RANDOM % 10000 + 100))
        DEATHS=$((RANDOM % 500))
        RECOVERED=$((RANDOM % 8000))
        ACTIVE=$((CASES - DEATHS - RECOVERED))
        TESTING=$((RANDOM % 50000 + 1000))
        
        echo "${DATE},State${REGION},${CASES},${DEATHS},${RECOVERED},${ACTIVE},${TESTING}" >> "ftp-data/prof1/datasets/${DATASET}.csv"
    done
    
    cp "ftp-data/prof1/datasets/${DATASET}.csv" "ftp-data/prof2/datasets/"
    echo "  ✓ Created dataset: ${DATASET}.csv (365 rows)"
done

# Add Excel versions of some datasets
echo ""
echo "Creating Excel format datasets..."
if command -v python3 &> /dev/null; then
    python3 << 'PYEOF'
import csv
import os

try:
    import openpyxl
    from openpyxl import Workbook
    
    for dataset in ['COVID_Cases_India_2020', 'Vaccination_Progress_2021']:
        for prof in ['prof1', 'prof2']:
            csv_file = f'ftp-data/{prof}/datasets/{dataset}.csv'
            xlsx_file = f'ftp-data/{prof}/datasets/{dataset}.xlsx'
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Data"
            
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    ws.append(row)
            
            wb.save(xlsx_file)
            print(f'  ✓ Created {xlsx_file}')
    
except ImportError:
    print("  ⚠ openpyxl not installed, skipping Excel generation")
    print("    Install with: pip3 install openpyxl")
PYEOF
fi

# Add README files with honey credentials
echo ""
echo "Creating README files with honey credentials..."

cat > ftp-data/guest/README.txt <<EOF
# PSRSC FTP Server - Guest Access

Welcome to the Pandemic Studies & Risk Surveillance Center FTP server.

Guest users have read-only access to shared resources.

For privileged access, contact:
- Prof. Rajesh Kumar (prof1@psrsc.iitk.ac.in)
- Prof. Priya Sharma (prof2@psrsc.iitk.ac.in)

INTERNAL NOTE (DO NOT SHARE):
SSH Access: dev-server.psrsc.local
Username: researcher
Password: P@ndemic2023!

VPN Config: vpn.psrsc.iitk.ac.in
Username: remote_access
Password: Secure#VPN$789

Last Updated: $(date)
EOF

cat > ftp-data/prof1/README.txt <<EOF
# Prof. Rajesh Kumar - Privileged Directory

RESTRICTED ACCESS - AUTHORIZED PERSONNEL ONLY

Contents:
- MoUs/      : Memoranda of Understanding with Government Ministries
- research/  : Classified research papers and reports
- datasets/  : Confidential pandemic surveillance data

Classification Level: SECRET
Clearance Required: GOI-PSRSC-PROF1

For data requests, use encrypted channel:
pgp-key: 0xABCD1234 (psrsc.iitk.ac.in/pgp/prof1.asc)

BACKUP CREDENTIALS (Emergency Access Only):
Database: postgresql://psrsc-db.local:5432/pandemic_data
Username: prof1_db
Password: DbAccess!Prof1#2023

Cloud Storage: https://storage.psrsc.iitk.ac.in
API Key: PSRSC-PROF1-${RANDOM}-${RANDOM}

Last Modified: $(date)
WARNING: Unauthorized access is a criminal offense.
EOF

cat > ftp-data/prof2/README.txt <<EOF
# Prof. Priya Sharma - Privileged Directory

RESTRICTED ACCESS - AUTHORIZED PERSONNEL ONLY

Contents:
- MoUs/      : Government collaboration agreements
- research/  : Confidential research publications
- datasets/  : Sensitive epidemiological data

Classification Level: SECRET
Clearance Required: GOI-PSRSC-PROF2

For secure communication:
Signal: +91-98765-XXXXX
ProtonMail: prof2.psrsc@protonmail.com

INTERNAL SYSTEMS ACCESS:
Analysis Server: analysis.psrsc.local
Username: priya.sharma
Password: Analyze#Data!456

Jenkins CI/CD: jenkins.psrsc.iitk.ac.in
Token: jenkins-prof2-${RANDOM}${RANDOM}

Last Modified: $(date)
WARNING: This directory is monitored. All access logged.
EOF

# Create a conspicuous "backup" directory with credentials
echo ""
echo "Creating backup credentials file (honey trap)..."
mkdir -p ftp-data/prof1/.backup
mkdir -p ftp-data/prof2/.backup

cat > ftp-data/prof1/.backup/system_credentials.txt <<EOF
# SYSTEM CREDENTIALS - BACKUP COPY
# Last Updated: $(date)

[WEB SERVER]
URL: http://psrsc.iitk.ac.in
Admin: admin@psrsc.local
Password: WebAdmin@2023!

[DATABASE]
Host: db.psrsc.local
Port: 5432
User: postgres
Password: Postgr3s!PSRSC

[SSH SERVERS]
dev-server: ssh researcher@dev.psrsc.local
Password: DevAccess!789

prod-server: ssh sysadmin@prod.psrsc.local
Password: ProdSys#2023!

[VPN]
Server: vpn.psrsc.iitk.ac.in
Username: prof1_vpn
Password: VPN!Access@123

[AWS]
Access Key: AKIA${RANDOM}${RANDOM}
Secret Key: $(openssl rand -base64 32)
Region: ap-south-1
EOF

cp ftp-data/prof1/.backup/system_credentials.txt ftp-data/prof2/.backup/

# Set proper permissions
echo ""
echo "Setting proper permissions..."
chmod -R 755 ftp-data/
chmod 644 ftp-data/*/*.txt
chmod 644 ftp-data/*/*/*.pdf
chmod 644 ftp-data/*/*/*.csv

# Generate summary
echo ""
echo "================================================"
echo "Fake Asset Generation Complete!"
echo "================================================"
echo ""
echo "Summary:"
echo "  Guest directory:"
echo "    - 1 README with honey credentials"
echo ""
echo "  Prof1 directory:"
echo "    - 7 fake MoU PDFs with Indian ministries"
echo "    - 12 fake research papers"
echo "    - 5 CSV datasets (365 rows each)"
echo "    - 1 README with honey credentials"
echo "    - 1 .backup folder with system credentials (trap)"
echo ""
echo "  Prof2 directory:"
echo "    - 7 fake MoU PDFs with Indian ministries"
echo "    - 12 fake research papers"
echo "    - 5 CSV datasets (365 rows each)"
echo "    - 1 README with honey credentials"
echo "    - 1 .backup folder with system credentials (trap)"
echo ""
echo "Total fake files: ~80 files"
echo ""
echo "Next steps:"
echo "  1. Review generated files: ls -lah ftp-data/"
echo "  2. Start FTP server: docker-compose up -d"
echo "  3. Test FTP access from Prof/Dev machines"
echo ""
