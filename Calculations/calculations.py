import xlwings as xw

import pandas as pd
from statistics import mean

import datetime as dt

## INPUTS

FILEPATH = "../Data/Customer Fill Template.xlsx"

# # Data Pull

# Here is we all the data is pulled from the Input Excel sheet that the field worker enters about the customer.
# 
# *NOTE:* These inputs are only for calcuations so far, not Quickbooks API integration.

app = xw.App()

# wb = xw.Book(FILEPATH)
wb = xw.books.active

## Get and clean room, door and accesory data
name = wb.names["Name"].refers_to_range.value


proj_typ = wb.names["ProjectType"].refers_to_range.value
tax = wb.names["Tax"].refers_to_range.value

room_defined_names = ["Names", "Width", "Depth", "Height", "Primer", "Finish", "CeilingServ","CeilingMat","BaseboardServ", "PrimerCoats", "FinishCoats"]
door_defined_names = ["Doors", "Quantity", "DoorCoat"]
acc_defined_names = ["Accessories", "Feet", "AccCoat"]

rooms = {name: wb.names[name].refers_to_range.value for name in room_defined_names}
doors = {name: wb.names[name].refers_to_range.value for name in door_defined_names}
accessories = {name: wb.names[name].refers_to_range.value for name in acc_defined_names}


# Remove data without area name and ensure all needed columns are filled
none_area = [i for i, val in enumerate(rooms['Names']) if val is None]
for col in rooms:
    rooms[col] = [val for i, val in enumerate(rooms[col]) if i not in none_area]
    # if None in rooms[col]: raise Exception("Please make sure all room information are filled in if area name is filled")

# Convert booleans

rooms['BaseboardServ'] = [True if bool=="Yes" else False for bool in rooms['BaseboardServ']]
rooms['CeilingServ'] = [True if bool=="Yes" else False for bool in rooms['CeilingServ']]


## TODO: Add HR SPECIAL LABOR COLUMN
rooms['HRLabor'] = [0]*len(rooms['Names'])

# Remove doors without quantity and ensure coats are filled if quanity is 
none_door = [i for i, val in enumerate(doors['Quantity']) if val in [None, 0]]
for type in doors:
    doors[type] = [val for i, val in enumerate(doors[type]) if i not in none_door]
    # if type=='DoorCoat' and  None in doors['DoorCoat']: raise Exception("Please make sure all door coats are filled in if quantity is filled")

# Remove accessories without quantity and ensure coats are filled if feet is 
none_acc = [i for i, val in enumerate(accessories['Feet']) if val in [None, 0]]
for type in accessories:
    accessories[type] = [val for i, val in enumerate(accessories[type]) if i not in none_acc]
    # if type=='AccCoat' and None in accessories['AccCoat']: raise Exception("Please make sure all accesory coats are filled in if feet is filled")


# %%
## Get paint data
DOORS_ACCESSORIES = pd.read_excel("../Data/Price.xlsx", sheet_name="Rates_Master_Paint")
PAINT = pd.read_excel("../Data/Price.xlsx", sheet_name="Paint_Prices")
PAINT.columns

# %%
# date = dt.datetime.now().strftime("%m%d%Y")
# NEWPATH = f"../Data/Customer Fill_{date}_{name}.xlsx"

# new_wb = wb.save(NEWPATH)

# wb.close()

# %% [markdown]
# # Python Calculations

# %%
LABOR_WALL = {
    "Commercial": 0.45,
    "Standard": 0.58,
    "Special": 0.68
}

HR_SPEC_LABOR_VAL = 65

PAINT_ceiling_max = PAINT[PAINT['Application'].str.contains('Ceiling')]['Price_Sf'].max()
PAINT_ceiling_min = PAINT[PAINT['Application'].str.contains('Ceiling')]['Price_Sf'].min()
PAINT_ceiling_median = PAINT[PAINT['Application'].str.contains('Ceiling')]['Price_Sf'].median()

PAINT_finish_min = PAINT[PAINT['Application'].str.contains('Finish')]['Price_Sf'].min()
PAINT_finish_median = PAINT[PAINT['Application'].str.contains('Finish')]['Price_Sf'].median()

PAINT_primer_min = PAINT[PAINT['Application'].str.contains('Primer')]['Price_Sf'].min()
PAINT_primer_median = PAINT[PAINT['Application'].str.contains('Primer')]['Price_Sf'].median()
PAINT_primer_avg = PAINT[PAINT['Application'].str.contains('Primer')]['Price_Sf'].mean()

PAINT_val = {
    "Commercial": mean([PAINT_ceiling_min, PAINT_finish_min, PAINT_primer_min]),
    "Standard": mean([PAINT_ceiling_median, PAINT_finish_median, PAINT_primer_median]),
    "Special": mean([PAINT_ceiling_max, PAINT_finish_median, PAINT_primer_avg])
}

# %%
room_calcs = {}

total_primer_gal = 0
total_area_all = 0



type = "Ceiling"  # "Ceiling" or "Wall"
# price_gal = c_price_gal if type == "Ceiling" else w_price_gal

## TODO: Add HR SPECIAL LABOR COLUMN

for i, room in enumerate(rooms['Names']):
    count =1 
    
    width = rooms['Width'][i]
    depth = rooms['Depth'][i]
    height = rooms['Height'][i]
    primer = rooms['Primer'][i]
    finish = rooms['Finish'][i]
    ceiling = rooms['CeilingServ'][i] 
    baseboard = rooms['BaseboardServ'][i]
    primer_coats = rooms['PrimerCoats'][i]
    finish_coats = rooms['FinishCoats'][i]
    hr_special_labor = rooms['HRLabor'][i]
    finish_type = rooms['CeilingMat'] if type == "Ceiling" else rooms['Finish']

    priming = rooms['CeilingMat'][i] if type == "Ceiling" else primer
    price_gal = PAINT[PAINT['Description']==primer]['Price_Customer'].values[0]

    # Areas 
    area_sf = 2*width*height + 2*depth*height if type != "Ceiling" else width * depth if ceiling else 0
    
    # Paint 
    primer_area = primer_coats * area_sf
    finish_area = finish_coats * area_sf

    total_area = primer_area + finish_area
    total_area_all += total_area

    coverage_priming = PAINT[PAINT['Description']==priming]['Coverage_Sf'].values[0]
    coverage_finish = PAINT[PAINT['Description']==finish]['Coverage_Sf'].values[0] if finish else 0

    finish_price_gal = PAINT[PAINT['Description']==finish]['Price_Customer'].values[0] if finish else 0

    primer_gal = primer_area / coverage_priming if coverage_priming!=0 else 0
    finish_gal = finish_area / coverage_finish if coverage_finish!=0 else 0

    total_primer_gal += primer_gal


    primer_paint_amt = primer_gal * price_gal 
    finish_paint_amt = finish_gal * finish_price_gal

    # Labor

    labor = total_area*LABOR_WALL[proj_typ]
    special_labor  = hr_special_labor * HR_SPEC_LABOR_VAL


    if room in room_calcs:
        total_area += room_calcs[room]["Total Area Sf"]
        count = room_calcs[room]["Count"] + 1

    room_calcs[room] = {
        "Total Area Sf": total_area,
        "Count": count
    }

room_calcs

# %%
def area_calculations(type, rooms):
    room_calcs = {}

    total_primer_gal = 0
    total_area_all = 0

    ## TODO: Add HR SPECIAL LABOR COLUMN

    for i, room in enumerate(rooms['Names']):
        count = 1

        width = rooms['Width'][i]
        depth = rooms['Depth'][i]
        height = rooms['Height'][i]
        primer = rooms['Primer'][i]
        finish = rooms['Finish'][i]
        ceiling = rooms['CeilingServ'][i] 
        baseboard = rooms['BaseboardServ'][i]
        primer_coats = rooms['PrimerCoats'][i]
        finish_coats = rooms['FinishCoats'][i]
        hr_special_labor = rooms['HRLabor'][i]
        finish_type = rooms['CeilingMat'] if type == "Ceiling" else rooms['Finish']

        priming = rooms['CeilingMat'][i] if type == "Ceiling" else primer
        price_gal = PAINT[PAINT['Description']==primer]['Price_Customer'].values[0]

        # Areas 
        area_sf = 2*width*height + 2*depth*height if type != "Ceiling" else width * depth if ceiling else 0
        
        
        # Paint 
        primer_area = primer_coats * area_sf
        finish_area = finish_coats * area_sf

        # if room =="Bedroom":
        #     print("Ceiling")
        #     print("Area Sf:", area_sf)
        #     print("Primer Area Sf:", primer_area)
        #     print("Finish Area Sf:", finish_area)

        total_area = primer_area + finish_area
        total_area_all += total_area

        coverage_priming = PAINT[PAINT['Description']==priming]['Coverage_Sf'].values[0]
        coverage_finish = PAINT[PAINT['Description']==finish]['Coverage_Sf'].values[0] if finish else 0

        finish_price_gal = PAINT[PAINT['Description']==finish]['Price_Customer'].values[0] if finish else 0

        primer_gal = primer_area / coverage_priming if coverage_priming!=0 else 0
        finish_gal = finish_area / coverage_finish if coverage_finish!=0 else 0

        total_primer_gal += primer_gal


        primer_paint_amt = primer_gal * price_gal 
        finish_paint_amt = finish_gal * finish_price_gal

        # Labor

        labor = total_area*LABOR_WALL[proj_typ]
        special_labor  = hr_special_labor * HR_SPEC_LABOR_VAL


        if room in room_calcs:
            total_area += room_calcs[room]["Total Area Sf"]
            count = room_calcs[room]["Count"] + 1

        room_calcs[room] = {
            "Total Area Sf": total_area,
            "Count": count
        }

    return room_calcs

# the Area and Paint sheet is split between Ceiling and Wall calculations so this adds them together

def calculate_totals(ceiling_calcs, wall_calcs):
    total_area = 0
    totals = {}

    for room in ceiling_calcs:
        total = ceiling_calcs[room]["Total Area Sf"] + wall_calcs[room]["Total Area Sf"]
        totals[room] = {
            "Total Area Sf": total
        }
        total_area += total

    return totals, total_area


def calc_initial_est(total):
    initial_est = LABOR_WALL[proj_typ] * total + PAINT_val[proj_typ]*total
    return initial_est


def door_accessories_calculations(type, df):
    calcs = {}
    table = DOORS_ACCESSORIES[DOORS_ACCESSORIES.Category==type.lower()]

    name = "Doors" if type=="Door" else "Accessories"
    coat = "DoorCoat" if type=="Door" else "AccCoat"
    quant = "Quantity" if type=="Door" else "Feet"

    for i in range(len(df[name])):
        da_type = df[name][i]
        coats = df[coat][i]
        qty = df[quant][i]

        coat_price = table[table["Item Name"] == da_type]["Value Per Unit"].values[0]
        price = coat_price * coats * qty
        calcs[da_type] = {
            "Total Price": price
        }

    total_price = sum([calcs[name]['Total Price'] for name in calcs])
    return calcs, total_price

def write(defined_name, val):
    wb.names[defined_name].refers_to_range.value = val
    wb.save()

# %%
wall_calcs = area_calculations("Wall", rooms)
print("Wall calculations:",wall_calcs)

ceiling_calcs = area_calculations("Ceiling", rooms)
print("Ceiling calculations:", ceiling_calcs)

all_calcs, total_area = calculate_totals(ceiling_calcs, wall_calcs)
print("Total for area:",all_calcs)
print("Total area:", total_area)

initial_est = calc_initial_est(total_area)
print("Initial Estimate:", initial_est)
    

# %%
door_calcs, door_total_price = door_accessories_calculations("Door", doors)
print("Door calculations:\n", door_calcs)

accessory_calcs, accessory_total_price = door_accessories_calculations("Accessory", accessories)
print("Accessory calculations:", accessory_calcs)

grand_total = initial_est + door_total_price + accessory_total_price
print("Grand Total Estimate:", grand_total)

# %%
# Write calculations to Excel

write("TotArea", total_area)
write("InitEst", round(initial_est, 2))

write("GranTotal", round(grand_total, 2))


