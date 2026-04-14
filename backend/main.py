from data_loader import load_all_structured_data

def main():
    datasets = load_all_structured_data()

    print("✅ Backend is running successfully\n")

    for name, df in datasets.items():
        print(f"{name} → {df.shape}")

if __name__ == "__main__":
    main()