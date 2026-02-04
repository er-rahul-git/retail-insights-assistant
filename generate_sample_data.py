
"""
Generate sample retail sales data for testing
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_sample_data(num_records=10000):
    """Generate sample retail sales data"""
    
    np.random.seed(42)
    random.seed(42)
    
    # Date range
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    # Categories and products
    categories = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books', 'Toys']
    regions = ['North', 'South', 'East', 'West', 'Central']
    customer_segments = ['Retail', 'Wholesale', 'Online', 'Enterprise']
    
    products = {
        'Electronics': ['Laptop', 'Phone', 'Tablet', 'Headphones', 'Camera'],
        'Clothing': ['Shirt', 'Pants', 'Dress', 'Jacket', 'Shoes'],
        'Home & Garden': ['Furniture', 'Decor', 'Garden Tools', 'Appliances'],
        'Sports': ['Bike', 'Weights', 'Yoga Mat', 'Running Shoes', 'Ball'],
        'Books': ['Fiction', 'Non-Fiction', 'Educational', 'Comics'],
        'Toys': ['Action Figure', 'Board Game', 'Puzzle', 'Doll']
    }
    
    data = []
    
    for i in range(num_records):
        # Random date
        days_between = (end_date - start_date).days
        random_days = random.randint(0, days_between)
        order_date = start_date + timedelta(days=random_days)
        
        # Category and product
        category = random.choice(categories)
        product = random.choice(products[category])
        
        # Other attributes
        region = random.choice(regions)
        segment = random.choice(customer_segments)
        
        # Sales metrics
        quantity = random.randint(1, 50)
        unit_price = round(random.uniform(10, 1000), 2)
        sales = round(quantity * unit_price, 2)
        cost = round(sales * random.uniform(0.4, 0.7), 2)
        profit = round(sales - cost, 2)
        discount = round(sales * random.uniform(0, 0.2), 2)
        
        data.append({
            'OrderID': f'ORD{i+1:06d}',
            'OrderDate': order_date,
            'Year': order_date.year,
            'Quarter': f'Q{(order_date.month-1)//3 + 1}',
            'Month': order_date.month,
            'Category': category,
            'Product': product,
            'Region': region,
            'CustomerSegment': segment,
            'Quantity': quantity,
            'UnitPrice': unit_price,
            'Sales': sales,
            'Cost': cost,
            'Profit': profit,
            'Discount': discount,
            'ProfitMargin': round((profit / sales) * 100, 2) if sales > 0 else 0
        })
    
    df = pd.DataFrame(data)
    
    # Sort by date
    df = df.sort_values('OrderDate').reset_index(drop=True)
    
    return df


if __name__ == "__main__":
    # Generate data
    print("Generating sample retail sales data...")
    df = generate_sample_data(10000)
    
    # Save to CSV
    output_file = 'data/sample_retail_data.csv'
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} records to {output_file}")
    
    # Display summary
    print("\nData Summary:")
    print(f"Date range: {df['OrderDate'].min()} to {df['OrderDate'].max()}")
    print(f"Total sales: ${df['Sales'].sum():,.2f}")
    print(f"Total profit: ${df['Profit'].sum():,.2f}")
    print(f"\nCategories: {df['Category'].nunique()}")
    print(f"Regions: {df['Region'].nunique()}")
    print(f"Products: {df['Product'].nunique()}")