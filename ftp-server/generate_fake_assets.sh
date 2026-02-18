#!/bin/bash
set -e

# Directory structure
mkdir -p ftp-data/guest
mkdir -p ftp-data/prof1/MoUs ftp-data/prof1/research ftp-data/prof1/datasets
mkdir -p ftp-data/prof2/MoUs ftp-data/prof2/research ftp-data/prof2/datasets

# Generate fake MoUs (PDFs)
for i in {1..7}; do
  echo "Fake MoU with Ministry $i" | enscript -B -o - | ps2pdf - ftp-data/prof1/MoUs/MoU_Ministry${i}.pdf
  echo "Fake MoU with Ministry $i" | enscript -B -o - | ps2pdf - ftp-data/prof2/MoUs/MoU_Ministry${i}.pdf
  sleep 1
done

# Generate fake research papers (PDFs)
for i in {1..12}; do
  echo "Fake Research Paper $i on Pandemic Studies" | enscript -B -o - | ps2pdf - ftp-data/prof1/research/Research_Paper${i}.pdf
  echo "Fake Research Paper $i on Pandemic Studies" | enscript -B -o - | ps2pdf - ftp-data/prof2/research/Research_Paper${i}.pdf
  sleep 1
done

# Generate fake datasets (CSV)
for i in {1..4}; do
  echo "date,cases,deaths" > ftp-data/prof1/datasets/dataset${i}.csv
  for d in {1..10}; do
    echo "2020-03-$d,$((RANDOM%1000)),$((RANDOM%50))" >> ftp-data/prof1/datasets/dataset${i}.csv
  done
  cp ftp-data/prof1/datasets/dataset${i}.csv ftp-data/prof2/datasets/
done

# Add README with honey credentials
for d in guest prof1 prof2; do
  echo -e "# Welcome to $d FTP\n\nHoney credentials: user=honeypot pass=trapme" > ftp-data/$d/README.txt
done

echo "Fake assets generated."
