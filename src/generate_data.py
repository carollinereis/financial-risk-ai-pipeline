import random
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

def generate_cpf() -> str:
    """Generates a validly formatted Brazilian CPF with check digits."""
    digits = [random.randint(0, 9) for _ in range(9)]

    # Compute 1st verification digit
    s = sum(d * w for d, w in zip(digits, range(10, 1, -1)))
    d1 = (s * 10) % 11
    digits.append(d1 if d1 < 10 else 0)

    # Compute 2nd verification digit
    s = sum(d * w for d, w in zip(digits, range(11, 1, -1)))
    d2 = (s * 10) % 11
    digits.append(d2 if d2 < 10 else 0)

    # Format as XXX.XXX.XXX-XX
    return f"{digits[0]}{digits[1]}{digits[2]}.{digits[3]}{digits[4]}{digits[5]}.{digits[6]}{digits[7]}{digits[8]}-{digits[9]}{digits[10]}"

def compute_default_probability(row: dict) -> float:
    """Simulates a realistic risk scoring engine using weighted financial metrics."""
    score = (
        0.35 * (1 - row["credit_score"] / 850)
        + 0.30 * row["debt_to_income_ratio"]
        + 0.25 * min(row["delinquencies_2yrs"] / 6, 1.0)
        + 0.10 * (1 - min(row["employment_length_years"] / 10, 1.0))
    )
    return min(max(score, 0.0), 1.0)

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "David", "Elizabeth", "Carlos", "Ana"]
LAST_NAMES = ["Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Silva", "Santos"]

def generate_synthetic_customers(num_records=100) -> pd.DataFrame:
    records = []

    # 1. Force Anchor Test Profiles
    anchors = [
        {
            "customer_id": 101, 
            "full_name": "Alice Smith", 
            "cpf": "123.456.789-00", 
            "email": "alice.smith@example.com", 
            "phone_number": "+55 11 98765-4321", 
            "credit_score": 580, 
            "debt_to_income_ratio": 0.45, 
            "delinquencies_2yrs": 2, 
            "annual_income": 55000, 
            "loan_amount_requested": 15000, 
            "employment_length_years": 2, 
            "is_high_risk": 1
        },
        {
            "customer_id": 102, 
            "full_name": "Bob Jones", 
            "cpf": "987.654.321-11", 
            "email": "bob.jones@example.com", 
            "phone_number": "+55 11 91234-5678", 
            "credit_score": 820, 
            "debt_to_income_ratio": 0.15, 
            "delinquencies_2yrs": 0, 
            "annual_income": 120000, 
            "loan_amount_requested": 20000, 
            "employment_length_years": 8, 
            "is_high_risk": 0
        },
        {
            "customer_id": 103, 
            "full_name": "Carlos Silva", 
            "cpf": "111.222.333-44", 
            "email": "carlos.silva@example.com", 
            "phone_number": "+55 21 99887-7665", 
            "credit_score": 510, 
            "debt_to_income_ratio": 0.58, 
            "delinquencies_2yrs": 3, 
            "annual_income": 42000, 
            "loan_amount_requested": 25000, 
            "employment_length_years": 1, 
            "is_high_risk": 1
        },
        {
            "customer_id": 104, 
            "full_name": "Diana Prince", 
            "cpf": "555.666.777-88", 
            "email": "diana.prince@example.com", 
            "phone_number": "+55 31 97766-5544", 
            "credit_score": 790, 
            "debt_to_income_ratio": 0.10, 
            "delinquencies_2yrs": 0, 
            "annual_income": 95000, 
            "loan_amount_requested": 10000, 
            "employment_length_years": 5, 
            "is_high_risk": 0
        },
    ]

    for a in anchors:
        a["underwriter_notes"] = f"Anchor profile test note for customer {a['customer_id']}"
        records.append(a)

    # 2. Generate Random Customers
    for i in range(105, 105 + num_records - len(anchors)):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10,99)}@example.com"
        cpf = generate_cpf()
        phone_number = f"+55 {random.choice([11, 21, 31, 41, 51])} 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"

        credit_score = random.randint(300, 850)
        dti = round(random.uniform(0.05, 0.65), 2)
        delinquencies = random.choices([0, 1, 2, 3, 4], weights=[0.6, 0.2, 0.1, 0.06, 0.04])[0]
        annual_income = round(random.uniform(25000, 150000), 2)
        loan_amount = round(random.uniform(5000, 40000), 2)
        employment = random.randint(0, 15)

        # Estimate risk probability ground truth
        prob = compute_default_probability({
            "credit_score": credit_score,
            "debt_to_income_ratio": dti,
            "delinquencies_2yrs": delinquencies,
            "annual_income": annual_income,
            "loan_amount_requested": loan_amount,
            "employment_length_years": employment
        })

        record = {
            "customer_id": i,
            "full_name": full_name,
            "cpf": cpf,
            "email": email,
            "phone_number": phone_number,
            "credit_score": credit_score,
            "debt_to_income_ratio": dti,
            "delinquencies_2yrs": delinquencies,
            "annual_income": annual_income,
            "loan_amount_requested": loan_amount,
            "employment_length_years": employment,
            "is_high_risk": int(prob >= 0.35),
            "underwriter_notes": f"Automated synthetic applicant profile for {full_name}."
        }
        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv("data/customers.csv", index=False)
    print("✓ Generated data/customers.csv with CPF, email, and phone fields.")
    return df

if __name__ == "__main__":
    generate_synthetic_customers()