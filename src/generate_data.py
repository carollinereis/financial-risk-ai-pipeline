import csv
import random
from pathlib import Path
from faker import Faker

# Use 'pt_BR' for realistic Brazilian CPFs, Phones, and Names
fake_br = Faker("pt_BR")
fake_en = Faker("en_US")

Faker.seed(42)
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CSV_FILE_PATH = DATA_DIR / "customers.csv"

# Predefined Anchor Customers with PII for deterministic testing
ANCHOR_CUSTOMERS = [
    {
        "customer_id": 101,
        "full_name": "Alice Smith",
        "email": "alice.smith@example.com",
        "phone": "(11) 97845-1308",
        "cpf": "123.456.789-00",
        "annual_income": 210000.0,
        "credit_score": 580,
        "debt_to_income_ratio": 0.45,
        "delinquencies_2yrs": 2,
        "loan_amount_requested": 60000.0,
        "employment_length_years": 8,
        "notes": "Customer Alice Smith (alice.smith@example.com, CPF: 123.456.789-00) requested a payment extension via phone (11) 97845-1308."
    },
    {
        "customer_id": 102,
        "full_name": "Bob Jones",
        "email": "bob.jones@example.com",
        "phone": "(21) 98765-4321",
        "cpf": "987.654.321-11",
        "annual_income": 32000.0,
        "credit_score": 820,
        "debt_to_income_ratio": 0.15,
        "delinquencies_2yrs": 0,
        "loan_amount_requested": 10000.0,
        "employment_length_years": 5,
        "notes": "Bob Jones has an excellent payment history with zero delinquencies."
    },
    {
        "customer_id": 103,
        "full_name": "Carlos Silva",
        "email": "carlos.silva@example.com",
        "phone": "(31) 99123-4567",
        "cpf": "456.789.012-22",
        "annual_income": 45000.0,
        "credit_score": 510,
        "debt_to_income_ratio": 0.58,
        "delinquencies_2yrs": 6,
        "loan_amount_requested": 35000.0,
        "employment_length_years": 1,
        "notes": "Carlos Silva called from (31) 99123-4567 regarding multiple late payments."
    },
    {
        "customer_id": 104,
        "full_name": "Diana Prince",
        "email": "diana.prince@example.com",
        "phone": "(41) 98888-7777",
        "cpf": "789.012.345-33",
        "annual_income": 115000.0,
        "credit_score": 790,
        "debt_to_income_ratio": 0.10,
        "delinquencies_2yrs": 0,
        "loan_amount_requested": 20000.0,
        "employment_length_years": 12,
        "notes": "Diana Prince pre-approved for priority risk tier."
    },
]


def generate_customer_dataset(total_records: int = 100) -> None:
    """Generates synthetic financial profiles saved directly to CSV."""
    fieldnames = [
        "customer_id",
        "full_name",
        "email",
        "phone",
        "cpf",
        "annual_income",
        "credit_score",
        "debt_to_income_ratio",
        "delinquencies_2yrs",
        "loan_amount_requested",
        "employment_length_years",
        "notes",
    ]

    customers = list(ANCHOR_CUSTOMERS)
    start_id = 105

    for i in range(total_records - len(ANCHOR_CUSTOMERS)):
        name = fake_br.name()
        first_name = name.split()[0]
        email = f"{first_name.lower()}{random.randint(10,99)}@example.com"
        phone = fake_br.cellphone_number()
        cpf = fake_br.cpf()

        customer = {
            "customer_id": start_id + i,
            "full_name": name,
            "email": email,
            "phone": phone,
            "cpf": cpf,
            "annual_income": round(random.uniform(25000, 250000), 2),
            "credit_score": random.randint(300, 850),
            "debt_to_income_ratio": round(random.uniform(0.05, 0.65), 2),
            "delinquencies_2yrs": random.choices([0, 1, 2, 3, 5], weights=[60, 20, 10, 7, 3])[0],
            "loan_amount_requested": round(random.uniform(5000, 80000), 2),
            "employment_length_years": random.randint(0, 20),
            "notes": f"Log entry for {name} ({email}, CPF: {cpf}, Phone: {phone}) regarding loan application.",
        }
        customers.append(customer)

    with open(CSV_FILE_PATH, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(customers)

    print(f"√ Generated {len(customers)} records in '{CSV_FILE_PATH}'")


if __name__ == "__main__":
    generate_customer_dataset(100)