#!/usr/bin/env python3
"""
Quick test to verify Supabase connection and templates data
"""

import os
from supabase import create_client

def test_supabase():
    url = 'https://ladviaautlfvpxuadqrb.supabase.co'
    key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
    
    print("Testing Supabase Connection...")
    client = create_client(url, key)
    
    try:
        # Test basic connection
        print("\nTesting prompt_templates table...")
        result = client.table('prompt_templates').select('*').eq('status', 'active').limit(5).execute()
        
        print(f"Found {len(result.data)} active templates")
        
        if result.data:
            sample = result.data[0]
            print(f"Sample template: {sample.get('name', 'N/A')}")
            print(f"Family: {sample.get('family_type', 'N/A')}")
            print(f"Category: {sample.get('template_category', 'N/A')}")
            print(f"Input fields: {sample.get('input_fields', 'N/A')}")
        
        # Get family types
        print("\nTesting family types...")
        family_result = client.table('prompt_templates').select('family_type').eq('status', 'active').execute()
        unique_families = list(set([t['family_type'] for t in family_result.data]))
        print(f"Found families: {unique_families}")
        
        # Get categories for first family
        if unique_families:
            first_family = unique_families[0]
            print(f"\nTesting categories for family '{first_family}'...")
            cat_result = client.table('prompt_templates').select('template_category').eq('family_type', first_family).eq('status', 'active').execute()
            unique_cats = list(set([t['template_category'] for t in cat_result.data]))
            print(f"Found categories: {unique_cats}")
            
            # Get templates for first category
            if unique_cats:
                first_cat = unique_cats[0]
                print(f"\nTesting templates for category '{first_cat}'...")
                template_result = client.table('prompt_templates').select('*').eq('family_type', first_family).eq('template_category', first_cat).eq('status', 'active').execute()
                print(f"Found {len(template_result.data)} templates in this category")
                
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    print(f"\nSupabase test completed successfully!")
    return True

if __name__ == "__main__":
    test_supabase()