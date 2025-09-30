"""
Create Kazakhstan Drink Sales Excel Data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create sample Kazakhstan drink sales data
months = pd.date_range(start='2024-01', periods=12, freq='M')

# Kazakhstan drink market data
drink_brands = {
    'Coca-Cola': {'category': 'Carbonated', 'market_share': 22},
    'Pepsi': {'category': 'Carbonated', 'market_share': 18},
    'Bonaqua': {'category': 'Water', 'market_share': 15},
    'Asem-Ai': {'category': 'Water', 'market_share': 12},
    'Dada': {'category': 'Juice', 'market_share': 10},
    'Gracio': {'category': 'Juice', 'market_share': 8},
    'Red Bull': {'category': 'Energy', 'market_share': 7},
    'Gorilla': {'category': 'Energy', 'market_share': 5},
    'Lipton': {'category': 'Tea', 'market_share': 3}
}

data_rows = []

for brand, info in drink_brands.items():
    base_sales = np.random.uniform(500000, 2000000)

    for i, month in enumerate(months):
        # Add seasonal variation (summer peak for drinks)
        seasonal_factor = 1 + 0.4 * np.sin(2 * np.pi * (i - 3) / 12)

        # Add growth trend
        growth = 1 + i * 0.015

        # Calculate sales
        sales_tenge = base_sales * seasonal_factor * growth
        units_sold = sales_tenge / np.random.uniform(150, 500)  # Price per unit in tenge

        data_rows.append({
            'Month': month.strftime('%Y-%m'),
            'Brand': brand,
            'Category': info['category'],
            'Sales (KZT)': round(sales_tenge, 2),
            'Units Sold': round(units_sold),
            'Market Share (%)': info['market_share'] + np.random.uniform(-2, 2),
            'Growth Rate (%)': np.random.uniform(5, 20) if i > 0 else 0,
            'Region': np.random.choice(['Almaty', 'Astana', 'Shymkent', 'Other']),
            'Distribution': np.random.choice(['Retail', 'HoReCa', 'Online'])
        })

# Create DataFrame
df = pd.DataFrame(data_rows)

# Save to Excel with multiple sheets
with pd.ExcelWriter('test_data.xlsx', engine='openpyxl') as writer:
    # Main data sheet
    df.to_excel(writer, sheet_name='Sales Data', index=False)

    # Summary by brand
    brand_summary = df.groupby('Brand').agg({
        'Sales (KZT)': 'sum',
        'Units Sold': 'sum',
        'Market Share (%)': 'mean'
    }).round(2)
    brand_summary.to_excel(writer, sheet_name='Brand Summary')

    # Summary by category
    category_summary = df.groupby('Category').agg({
        'Sales (KZT)': 'sum',
        'Units Sold': 'sum',
        'Market Share (%)': 'sum'
    }).round(2)
    category_summary.to_excel(writer, sheet_name='Category Summary')

    # Monthly trends
    monthly_summary = df.groupby('Month').agg({
        'Sales (KZT)': 'sum',
        'Units Sold': 'sum'
    }).round(2)
    monthly_summary.to_excel(writer, sheet_name='Monthly Trends')

print("Created test_data.xlsx with Kazakhstan drink sales data")
print(f"Total rows: {len(df)}")
print(f"Brands: {', '.join(drink_brands.keys())}")
print(f"Categories: {', '.join(set(info['category'] for info in drink_brands.values()))}")