# CBAM Benchmark Calculation Flow - Complete Guide with Examples

## Overview

This document explains how CBAM benchmark values are calculated and fetched after the recent updates, including the new `year` field integration.

---

## 1. Complete Flow Diagram

```
External Good Created/Saved
    ↓
validate() called
    ↓
set_year_from_report() → Extracts year from CBAM Report dates
    ↓
calculate_benchmark() → Uses year field to create reference date
    ↓
calculate_country_specific_benchmark(cn_code, country, reference_date)
    ↓
Multi-Tier Fallback System:
    1. Country Default Benchmark (for country + CN code)
    2. Global Default Benchmark (for CN code only)
    ↓
Get CBAM Benchmark (using year from reference_date)
    ↓
Calculate: CBAM Benchmark Value × Multiplication Factor
    ↓
Store in: country_specific_default_cbam_benchmark
```

---

## 2. Step-by-Step Process with Examples

### Example Scenario
- **External Good**: EX-G-00105
- **CN Code**: 73181100 (Steel products)
- **Installation Country**: Germany
- **CBAM Report**: CR-2025-Q1
- **Report Dates**: from_date = 2025-01-01, to_date = 2025-03-31
- **Year Field**: 2025 (auto-set from report dates)

---

### Step 1: External Good Creation/Save

**When External Good is created from CBAM Report:**

```python
# In external_good.py - validate() method
def validate(self):
    self.set_year_from_report()  # Sets year = 2025
    self.calculate_benchmark()   # Calculates benchmark
```

**What happens:**
1. `set_year_from_report()` checks if `report_id` exists and `year` is not set
2. Gets CBAM Report: `CR-2025-Q1`
3. Extracts year from `from_date` (2025-01-01) → year = 2025
4. Gets or creates Year record "2025"
5. Sets `self.year = "2025"`

---

### Step 2: Benchmark Calculation Triggered

**In `calculate_benchmark()` method:**

```python
def calculate_benchmark(self):
    # Use year field if available
    reference_date = None
    if self.year:  # year = "2025"
        year_value = frappe.db.get_value("Year", self.year, "year")  # Gets 2025
        if year_value:
            from datetime import date
            reference_date = date(2025, 1, 1)  # Creates date(2025, 1, 1)
    
    result = calculate_country_specific_benchmark(
        self.cn_code,           # "73181100"
        self.installation_country,  # "Germany"
        reference_date          # date(2025, 1, 1)
    )
```

**Key Point:** The `year` field is now used to create a proper reference date (January 1st of that year) instead of using `None`.

---

### Step 3: Multi-Tier Benchmark Lookup

**In `calculate_country_specific_benchmark()` function:**

```python
def calculate_country_specific_benchmark(cn_code, country, reference_date=None):
    # Step 1: Determine reference year
    if reference_date:  # date(2025, 1, 1)
        reference_year = reference_date.year  # = 2025
    else:
        reference_year = today().year  # Fallback to current year
    
    # Step 2: Try Country Default Benchmark first
    cdb = get_country_default_benchmark("Germany", "73181100")
    
    # Step 3: If not found, try Global Default Benchmark
    if not cdb:
        cdb = get_global_default_benchmark("73181100")
    
    # Step 4: Get CBAM Benchmark using the year
    cbam_benchmark = get_cbam_benchmark("73181100", indicator, 2025)
    
    # Step 5: Calculate final value
    result = cbam_benchmark_value × multiplication_factor
```

---

### Step 4: Country Default Benchmark Lookup

**Example: Looking for Germany + CN Code 73181100**

```python
def get_country_default_benchmark(country, cn_code):
    # Query: Find Country Default Benchmark for Germany
    cdb_docs = frappe.get_all("Country Default Benchmark",
        filters={"country": "Germany", "is_global_default": 0},
        fields=["name"]
    )
    
    # Found: CDB-Germany-0001
    cdb_doc = frappe.get_doc("Country Default Benchmark", "CDB-Germany-0001")
    
    # Check benchmark_values table for matching CN code
    for row in cdb_doc.benchmark_values:
        if row.cn_code == "73181100":  # Match found!
            return {
                "cbam_benchmark_indicator": "(C) Carbon Steel based on BF/BOF",
                "benchmark_multiplication_factor": 1.0
            }
```

**Result:** Found indicator `(C) Carbon Steel based on BF/BOF` with factor `1.0`

---

### Step 5: CBAM Benchmark Lookup (Year-Based)

**Example: Looking for CN Code 73181100, Indicator (C), Year 2025**

```python
def get_cbam_benchmark(cn_code, indicator, year):
    # year = 2025 (from reference_date.year)
    
    # Find CBAM Benchmark for CN code 73181100
    cbam_docs = frappe.get_all("CBAM Benchmark",
        filters={"cn_code": "73181100"},
        fields=["name", "valid_from_year", "valid_to_year"]
    )
    
    # Check each benchmark for valid date range
    for cbam_doc in cbam_docs:
        from_year = frappe.db.get_value("Year", cbam_doc.valid_from_year, "year")  # e.g., 2024
        to_year = frappe.db.get_value("Year", cbam_doc.valid_to_year, "year")      # e.g., 2025
        
        # Check if 2025 is in range [2024, 2025]
        if from_year <= 2025 <= to_year:  # Valid!
            cbam = frappe.get_doc("CBAM Benchmark", cbam_doc.name)
            
            # Find matching indicator in benchmark_values table
            for row in cbam.benchmark_values:
                if row.cbam_benchmark_indicator == "(C) Carbon Steel based on BF/BOF":
                    return {
                        "emission_benchmark": 1.8  # tCO2/tproduct
                    }
```

**Result:** Found emission benchmark `1.8 tCO2/tproduct` for year 2025

---

### Step 6: Final Calculation

**Calculate the final benchmark value:**

```python
# From Step 4:
indicator = "(C) Carbon Steel based on BF/BOF"
factor = 1.0

# From Step 5:
base_value = 1.8  # tCO2/tproduct

# Final calculation:
result = base_value × factor
result = 1.8 × 1.0
result = 1.8
```

**Stored in External Good:**
- `country_specific_default_cbam_benchmark` = 1.8
- `benchmark_calculation_status` = "Calculated"
- `benchmark_calculation_details` = JSON with source, indicator, factor, etc.

---

## 3. Fallback Scenarios

### Scenario A: No Country-Specific Benchmark

**Example:** External Good for India + CN Code 73181100

```
Step 1: Try Country Default Benchmark for India
    → Not found
    
Step 2: Try Global Default Benchmark
    → Found! Uses global default
    
Step 3: Get CBAM Benchmark (same as before)
    → Found indicator and value
    
Result: Uses global default indicator and factor
Status: "Calculated" with source = "global_default"
```

### Scenario B: No CBAM Benchmark for Year

**Example:** External Good for year 2026, but CBAM Benchmark only valid until 2025

```
Step 1: Country Default Benchmark found
Step 2: Try to get CBAM Benchmark for year 2026
    → No valid benchmark found (2026 > 2025)
    
Result: benchmark_value = None
Status: "Missing Data"
Details: "No CBAM Benchmark: CN 73181100, Indicator (C), Year 2026"
```

### Scenario C: Missing Year Field (Old Records)

**Example:** External Good created before year field was added

```
Step 1: year field is None
Step 2: reference_date = None
Step 3: Uses current year as fallback
    reference_year = today().year  # e.g., 2025
    
Result: Works but uses current year instead of report year
Note: Run update script to backfill year field
```

---

## 4. Real-World Example: Complete Flow

### Input Data:
- **External Good Name**: EX-G-00105
- **CN Code**: 73181100
- **Installation Country**: Germany
- **CBAM Report**: CR-2025-Q1
- **Report from_date**: 2025-01-01
- **Report to_date**: 2025-03-31

### Database Records:

**1. Country Default Benchmark:**
```
Name: CDB-Germany-0001
Country: Germany
Is Global Default: No
Benchmark Values:
  - CN Code: 73181100
  - Indicator: (C) Carbon Steel based on BF/BOF
  - Factor: 1.0
```

**2. CBAM Benchmark:**
```
Name: CB-BM-73181100-001
CN Code: 73181100
Valid From Year: 2024
Valid To Year: 2025
Benchmark Values:
  - Indicator: (C) Carbon Steel based on BF/BOF
  - Emission Benchmark: 1.8 tCO2/tproduct
```

**3. Year Record:**
```
Name: 2025
Year: 2025
```

### Calculation Process:

1. **External Good saved** → `validate()` called
2. **Year extracted** → `year = "2025"` (from report dates)
3. **Reference date created** → `date(2025, 1, 1)`
4. **Country Default found** → Indicator: `(C)`, Factor: `1.0`
5. **CBAM Benchmark found** → Value: `1.8` (valid for year 2025)
6. **Final calculation** → `1.8 × 1.0 = 1.8`
7. **Stored** → `country_specific_default_cbam_benchmark = 1.8`

### Final Result in External Good:

```json
{
  "name": "EX-G-00105",
  "cn_code": "73181100",
  "installation_country": "Germany",
  "year": "2025",
  "country_specific_default_cbam_benchmark": 1.8,
  "benchmark_calculation_status": "Calculated",
  "benchmark_calculation_details": {
    "cn_code": "73181100",
    "country": "Germany",
    "reference_year": 2025,
    "indicator_used": "(C) Carbon Steel based on BF/BOF",
    "factor_used": 1.0,
    "base_value": 1.8,
    "calculated_value": 1.8,
    "source": "country_specific"
  }
}
```

---

## 5. Key Improvements After Updates

### Before Updates:
- ❌ No year field → Used `None` as reference date
- ❌ Always used current year → Not accurate for historical data
- ❌ Manual year extraction needed in reports

### After Updates:
- ✅ Year field automatically set from CBAM Report dates
- ✅ Accurate year-based benchmark lookups
- ✅ Proper date handling with `date(2025, 1, 1)` format
- ✅ Year stored in database for reporting and filtering
- ✅ Automatic year extraction during validation

---

## 6. Usage in Reports

### Financial Evaluation Report:

```sql
SELECT 
    eg.cn_code,
    eg.country_specific_default_cbam_benchmark AS bench_mark,
    -- Uses stored value directly (fast!)
FROM `tabExternal Good` eg
```

**Before:** Had to calculate on-the-fly (slow)  
**After:** Uses stored `country_specific_default_cbam_benchmark` (fast)

### Financial Exposure Forecast:

```python
# Gets year from External Good
year = eg.year  # "2025"
year_value = frappe.db.get_value("Year", year, "year")  # 2025

# Uses year for accurate benchmark lookup
benchmark = eg.country_specific_default_cbam_benchmark  # 1.8
```

---

## 7. Summary

The CBAM benchmark calculation now:

1. **Automatically extracts year** from CBAM Report dates when External Good is created/saved
2. **Uses year for accurate lookups** - ensures correct CBAM Benchmark is found based on report period
3. **Stores calculated value** - `country_specific_default_cbam_benchmark` for fast report generation
4. **Follows multi-tier fallback** - Country Default → Global Default → Error
5. **Handles edge cases** - Missing data, invalid years, etc.

The year field ensures that benchmarks are calculated using the correct time period, making the system more accurate and reliable for CBAM reporting.
