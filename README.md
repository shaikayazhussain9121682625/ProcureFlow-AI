# ProcureFlow AI

## Overview
Synthetic procurement workflow and data generation application built using Python and Flask.

## Technologies
Python, Flask, Flask-SQLAlchemy, SQLite, Faker, Pandas, Pytest, HTML, CSS and JavaScript.

## Workflow
1. Purchase requests
2. Budget validation
3. Multi-level approvals
4. RFQ generation
5. Supplier quotations
6. Quote comparison
7. Purchase orders
8. Delivery tracking
9. Audit events
10. Anomaly verification

## Dataset
- 10 departments
- 300 requesters
- 50 budgets
- 1,200 purchase requests
- 120 suppliers
- 1,183 RFQs
- 3,549 supplier quotes
- 1,306 approvals
- 1,183 purchase orders
- 1,183 deliveries
- 9,488 audit events

## Anomaly Scenarios
Seven verified cases:
- Purchase order without approval
- Expired quotation
- Non-cheapest supplier selection
- Inactive supplier
- Budget overrun
- Duplicate purchase request
- Quote currency mismatch

Ground truth: exports/ground_truth/anomaly_ground_truth.csv

## Installation
1. Create virtual environment: python -m venv venv
2. Activate: .\venv\Scripts\Activate.ps1
3. Install: python -m pip install -r requirements.txt
4. Run: python app.py

## Export Commands
- python -m generator.export_all
- python -m generator.export_sql
- python -m generator.create_data_dictionary

## Testing
Run: python -m pytest -v

## Validation Results
- 53 database integrity checks passed
- 6 automated tests passed
- 7 of 7 anomaly types verified
- 30 CSV and JSON files passed checksum comparison
- 34,818 normal export records

## Data Privacy
All procurement records are synthetic. Ground-truth labels are kept separate from normal exports.

## Random Seed
20261022

## Project Objective
Demonstrate an explainable procurement workflow with approvals, supplier comparison, exception handling, data validation and audit traceability.
