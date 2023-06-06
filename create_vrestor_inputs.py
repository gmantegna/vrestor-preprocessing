import pandas as pd
import numpy as np
import os
path = os.getcwd()
from pathlib import Path

# parameters

case_folder = Path("./case_1")
fom_cost_allocation = {
    "pv":0.63,
    "gcc":0.1,
    "inverter":0.27
}
zero_out_storage_costs = True

storage_type = "LDES" # LDES or Battery (NOTE: cost functionality only works for Battery)

if storage_type == "LDES":
    storage_tech_str = "MetalAir"
    self_disch = 0
    eff_up = 0.65
    eff_down = 0.65
    etainverter=0.967
    power_to_energy_ratio = 1 / 200
elif storage_type =="Battery":
    storage_tech_str = "Battery"
    self_disch = 0.05
    eff_up = 0.95
    eff_down = 0.95
    etainverter=0.967
    power_to_energy_ratio = 0.25
else:
    raise ValueError("not a valid storage type")


# NREL 2021 Co-location study breakdown (see excel sheet for how these values were actually broken down)
cur_pv_cost_per_mw_ac = 1309972
cur_storage_cost_per_mwh_ac = 424189

cur_pv_cost_per_mw_dc = 811187
cur_storage_cost_per_mwh_dc = 405377
cur_inverter_cost_per_mw_ac = 132508

standalone_battery_gcc = 2560 #annuitized interconnection fee in 2022$

##############

#### get cost breakdown and store as "output" df

if os.path.exists(case_folder / "Generators_data_before_vrestor.csv"):
    generators_data = pd.read_csv(case_folder / "Generators_data_before_vrestor.csv")
else:
    generators_data = pd.read_csv(case_folder / "Generators_data.csv")
generators_data["R_ID"] = generators_data.index + 1

output = pd.DataFrame()

# get DC costs based on difference between current cost and cost in generators_data

pv_generators = generators_data[generators_data.technology.str.contains("UtilityPV")].copy(deep=True)
pv_capex_mw_future = pv_generators.capex_mw.iloc[0]
pv_cost_decrease_ratio = pv_capex_mw_future / cur_pv_cost_per_mw_ac
pv_cost_per_mw_dc = cur_pv_cost_per_mw_dc * pv_cost_decrease_ratio # DC dropped values for year
inverter_cost_per_mw_ac = cur_inverter_cost_per_mw_ac * pv_cost_decrease_ratio # DC dropped values for year

storage_generators = generators_data[generators_data.technology.str.contains(storage_tech_str)].copy(deep=True)
storage_capex_mwh_future = storage_generators.capex_mwh.iloc[0] + storage_generators.capex_mw.iloc[0]/(1/power_to_energy_ratio)
storage_cost_decrease_ratio = storage_capex_mwh_future / cur_storage_cost_per_mwh_ac # DC dropped values for year
storage_cost_per_mwh_dc = cur_storage_cost_per_mwh_dc * storage_cost_decrease_ratio # DC dropped values for year

# make hybrid pv resources

hybrid_pv = pv_generators[["region","Resource","technology"]].copy(deep=True)
hybrid_pv.technology = "hybrid_pv"
storage_financial_parameters = storage_generators[["region","wacc_real","cap_recovery_years","regional_cost_multiplier","Fixed_OM_Cost_per_MWhyr"]].rename(columns={
    "wacc_real":"storage_wacc_real",
    "cap_recovery_years":"storage_cap_recovery_years",
    "regional_cost_multiplier":"storage_regional_cost_multiplier",
    "Fixed_OM_Cost_per_MWhyr":"storage_fom_per_mwh_yr",
}) 
index_before = pv_generators.index
pv_generators = pd.merge(pv_generators,storage_financial_parameters,on="region")
pv_generators.index = index_before

hybrid_pv["Inv_Cost_per_MWyr"] = pv_generators["interconnect_annuity"]
crf = (
    np.exp(pv_generators.wacc_real*pv_generators.cap_recovery_years)
    *(np.exp(pv_generators.wacc_real)-1)
)/(
    np.exp(pv_generators.wacc_real*pv_generators.cap_recovery_years)-1
)
crf_storage = (
    np.exp(pv_generators.storage_wacc_real*pv_generators.storage_cap_recovery_years)
    *(np.exp(pv_generators.storage_wacc_real)-1)
)/(
    np.exp(pv_generators.storage_wacc_real*pv_generators.storage_cap_recovery_years)-1
)

hybrid_pv["Inv_Cost_Inverter_per_MWyr"] = inverter_cost_per_mw_ac * pv_generators["storage_regional_cost_multiplier"] * crf_storage
hybrid_pv["Inv_Cost_Solar_per_MWyr"] = pv_cost_per_mw_dc * pv_generators["regional_cost_multiplier"] * crf
hybrid_pv["Inv_Cost_Wind_per_MWyr"] = 0

if zero_out_storage_costs:
    hybrid_pv["Inv_Cost_per_MWhyr"] = 0
else:
    hybrid_pv["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * pv_generators["storage_regional_cost_multiplier"] * crf_storage
hybrid_pv["Fixed_OM_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["gcc"]
hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["inverter"]
hybrid_pv["Fixed_OM_Solar_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["pv"]
hybrid_pv["Fixed_OM_Wind_Cost_per_MWyr"] = 0
if zero_out_storage_costs:
    hybrid_pv["Fixed_OM_Cost_per_MWhyr"] = 0
else:
    hybrid_pv["Fixed_OM_Cost_per_MWhyr"] = pv_generators["storage_fom_per_mwh_yr"]

output = pd.concat([output,hybrid_pv],axis=0)

# make hybrid wind resources

wind_generators = generators_data[generators_data.technology.str.contains("LandbasedWind")].copy(deep=True)
hybrid_wind = wind_generators[["region","Resource","technology"]].copy(deep=True)
hybrid_wind.technology = "hybrid_wind"
storage_financial_parameters = storage_generators[["region","wacc_real","cap_recovery_years","regional_cost_multiplier","Fixed_OM_Cost_per_MWhyr"]].rename(columns={
    "wacc_real":"storage_wacc_real",
    "cap_recovery_years":"storage_cap_recovery_years",
    "regional_cost_multiplier":"storage_regional_cost_multiplier",
    "Fixed_OM_Cost_per_MWhyr":"storage_fom_per_mwh_yr",
})
index_before = wind_generators.index
wind_generators = pd.merge(wind_generators,storage_financial_parameters,on="region")
wind_generators.index = index_before

hybrid_wind["Inv_Cost_per_MWyr"] = wind_generators["interconnect_annuity"]
crf = (
    np.exp(wind_generators.wacc_real*wind_generators.cap_recovery_years)
    *(np.exp(wind_generators.wacc_real)-1)
)/(
    np.exp(wind_generators.wacc_real*wind_generators.cap_recovery_years)-1
)
crf_storage = (
    np.exp(wind_generators.storage_wacc_real*wind_generators.storage_cap_recovery_years)
    *(np.exp(wind_generators.storage_wacc_real)-1)
)/(
    np.exp(wind_generators.storage_wacc_real*wind_generators.storage_cap_recovery_years)-1
)

hybrid_wind["Inv_Cost_Inverter_per_MWyr"] = inverter_cost_per_mw_ac * wind_generators["storage_regional_cost_multiplier"] * crf_storage
hybrid_wind["Inv_Cost_Solar_per_MWyr"] = 0
hybrid_wind["Inv_Cost_Wind_per_MWyr"] = wind_generators["Inv_Cost_per_MWyr"] - wind_generators["interconnect_annuity"]
if zero_out_storage_costs:
    hybrid_wind["Inv_Cost_per_MWhyr"] = 0
else:
    hybrid_wind["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * wind_generators["storage_regional_cost_multiplier"] * crf_storage


## NOTE: currently assuming FOM for GCC and inverter for hybrid wind are the same as for hybrid pv.
hybrid_wind["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
hybrid_wind["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
hybrid_wind["Fixed_OM_Solar_Cost_per_MWyr"] = 0
hybrid_wind["Fixed_OM_Wind_Cost_per_MWyr"] = wind_generators["Fixed_OM_Cost_per_MWyr"] - hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]

if zero_out_storage_costs:
    hybrid_wind["Fixed_OM_Cost_per_MWhyr"] = 0
else:
    hybrid_wind["Fixed_OM_Cost_per_MWhyr"] = wind_generators["storage_fom_per_mwh_yr"]

output = pd.concat([output,hybrid_wind],axis=0)

# make standalone storage resources
standalone_storage = storage_generators[["region","Resource","technology"]].copy(deep=True)
standalone_storage.technology = "standalone_storage"

crf = (
    np.exp(storage_generators.wacc_real*storage_generators.cap_recovery_years)
    *(np.exp(storage_generators.wacc_real)-1)
)/(
    np.exp(storage_generators.wacc_real*storage_generators.cap_recovery_years)-1
)

standalone_storage["Inv_Cost_per_MWyr"] = standalone_battery_gcc
standalone_storage["Inv_Cost_Inverter_per_MWyr"] = inverter_cost_per_mw_ac * storage_generators["regional_cost_multiplier"] * crf
standalone_storage["Inv_Cost_Solar_per_MWyr"] = 0
standalone_storage["Inv_Cost_Wind_per_MWyr"] = 0

if zero_out_storage_costs:
    standalone_storage["Inv_Cost_per_MWhyr"] = 0
else:
    standalone_storage["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * storage_generators["regional_cost_multiplier"] * crf

# once again assuming FOM for GCC and inverter are same as for hybrid pv
standalone_storage["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
standalone_storage["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
standalone_storage["Fixed_OM_Solar_Cost_per_MWyr"] = 0
standalone_storage["Fixed_OM_Wind_Cost_per_MWyr"] = 0

if zero_out_storage_costs:
    standalone_storage["Fixed_OM_Cost_per_MWhyr"] = 0
else:
    standalone_storage["Fixed_OM_Cost_per_MWhyr"] = storage_generators["Fixed_OM_Cost_per_MWhyr"]

cost_breakdown = pd.concat([output,standalone_storage],axis=0)

cost_breakdown.rename(columns={"technology":"Resource_Type"},inplace=True)
cost_breakdown.drop(columns="region",inplace=True)

#### make Vre_stor_data.csv

vrestor_data = pd.merge(
    generators_data[generators_data.Resource.isin(cost_breakdown.Resource)].copy(deep=True),
    cost_breakdown,
    on="Resource"
)
vrestor_data["SOLAR"] = 0
vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","SOLAR"] = 1
vrestor_data["WIND"] = 0
vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","WIND"] = 1
vrestor_data["STOR_DC_DISCHARGE"] = 1
vrestor_data["STOR_DC_CHARGE"] = 1

# transfer any active MinCap constraints to all VREStor resources. Currently sets the MinCapTag_MWh_x column to 1 and the regular mincap column to 0
for mincap_column in vrestor_data.columns[vrestor_data.columns.str.contains("MinCap")]:
    new_mincap_column_name = "MinCapTag_MWh" + mincap_column.split("_")[1]
    regions_with_active_mincap = pd.unique(vrestor_data[vrestor_data[mincap_column]==1].region)
    vrestor_data[new_mincap_column_name] = 0
    vrestor_data.loc[vrestor_data.region.isin(regions_with_active_mincap),new_mincap_column_name] = 1
    vrestor_data[mincap_column] = 0

# transfer any active MaxCap constraints to all VREStor resources. Currently sets the MaxCapTag_MWh_x column to 1 and the regular maxcap column to 0
for maxcap_column in vrestor_data.columns[vrestor_data.columns.str.contains("MaxCap")]:
    new_maxcap_column_name = "MaxCapTag_MWh" + maxcap_column.split("_")[1]
    regions_with_active_maxcap = pd.unique(vrestor_data[vrestor_data[maxcap_column]==1].region)
    vrestor_data[new_maxcap_column_name] = 0
    vrestor_data.loc[vrestor_data.region.isin(regions_with_active_maxcap),new_maxcap_column_name] = 1
    vrestor_data[maxcap_column] = 0

for col_name in ["STOR_AC_DISCHARGE","STOR_AC_CHARGE","Existing_Cap_Inverter_MW","Existing_Cap_Solar_MW","Existing_Cap_Wind_MW","Existing_Cap_Charge_DC_MW","Existing_Cap_Charge_AC_MW","Existing_Cap_Discharge_DC_MW","Existing_Cap_Discharge_AC_MW","Max_Cap_Inverter_MW","Min_Cap_Inverter_MW","Max_Cap_Charge_AC_MW","Min_Cap_Charge_AC_MW","Max_Cap_Discharge_AC_MW","Min_Cap_Discharge_AC_MW","Max_Cap_Charge_DC_MW","Min_Cap_Charge_DC_MW","Max_Cap_Discharge_DC_MW","Min_Cap_Discharge_DC_MW","Min_Cap_Solar_MW","Min_Cap_Wind_MW","Inv_Cost_Discharge_DC_per_MWyr","Inv_Cost_Charge_DC_per_MWyr","Inv_Cost_Discharge_AC_per_MWyr","Inv_Cost_Charge_AC_per_MWyr","Fixed_OM_Cost_Discharge_DC_per_MWyr","Fixed_OM_Cost_Charge_DC_per_MWyr","Fixed_OM_Cost_Discharge_AC_per_MWyr","Fixed_OM_Cost_Charge_AC_per_MWyr","Var_OM_Cost_per_MWh_Solar","Var_OM_Cost_per_MWh_Wind","Var_OM_Cost_per_MWh_Charge_AC","Var_OM_Cost_per_MWh_Discharge_AC"]:
    vrestor_data[col_name] = 0
for col_name in ["Max_Cap_Inverter_MW","Min_Cap_Inverter_MW","Max_Cap_Charge_AC_MW","Min_Cap_Charge_AC_MW","Max_Cap_Discharge_AC_MW","Min_Cap_Discharge_AC_MW","Max_Cap_Charge_DC_MW","Min_Cap_Charge_DC_MW","Max_Cap_Discharge_DC_MW","Max_Cap_Solar_MW","Max_Cap_Wind_MW","Inverter_Ratio_Wind","Inverter_Ratio_Solar"]:
    vrestor_data[col_name] = -1

vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Max_Cap_Solar_MW"] = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Max_Cap_MW"]
vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","Max_Cap_Wind_MW"] = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","Max_Cap_MW"]

vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Var_OM_Cost_per_MWh_Solar"] = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Var_OM_Cost_per_MWh"]
vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","Var_OM_Cost_per_MWh_Wind"] = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","Var_OM_Cost_per_MWh"]

vrestor_data["Var_OM_Cost_per_MWh_Charge_DC"] = 0.15
vrestor_data["Var_OM_Cost_per_MWh_Discharge_DC"] = 0.15

vrestor_data["Self_Disch"] = self_disch
vrestor_data["Eff_Up_DC"] = eff_up
vrestor_data["Eff_Down_DC"] = eff_down
vrestor_data["Eff_Up_AC"] = eff_up
vrestor_data["Eff_Down_AC"] = eff_down

vrestor_data["EtaInverter"] = etainverter
vrestor_data["Power_to_Energy_DC"] = power_to_energy_ratio
vrestor_data["Power_to_Energy_AC"] = power_to_energy_ratio

if storage_type == "LDES":
    vrestor_data["LDS"] = 1

#### modify generators_data

gendata_mod = generators_data.copy(deep=True)
vrestor_resources = vrestor_data.Resource

# reset relevant columns
for capres_column in gendata_mod.columns[gendata_mod.columns.str.contains("CapRes")]:
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),capres_column] = 0
for mincap_column in gendata_mod.columns[gendata_mod.columns.str.contains("MinCap")]:
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),mincap_column] = 0
for maxcap_column in gendata_mod.columns[gendata_mod.columns.str.contains("MaxCap")]:
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),maxcap_column] = 0
for esr_column in gendata_mod.columns[gendata_mod.columns.str.contains("ESR")]:
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),esr_column] = 0
for col_name in ["VRE","STOR","Var_OM_Cost_per_MWh","Var_OM_Cost_per_MWh_In","Eff_Up","Eff_Down","Min_Duration","Max_Duration","Ramp_Up_Percentage","Ramp_Dn_Percentage","Commit","Num_VRE_Bins","LDS"]:
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),col_name] = 0
gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"Max_Cap_MW"] = -1
gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"Max_Cap_MWh"] = -1
gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"Self_Disch"] = self_disch
gendata_mod["VRE_STOR"] = 0
gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"VRE_STOR"] = 1

# get costs from cost_breakdown
gendata_mod.set_index("Resource",inplace=True)
for cost_category in ["Inv_Cost_per_MWyr","Fixed_OM_Cost_per_MWyr","Inv_Cost_per_MWhyr","Fixed_OM_Cost_per_MWhyr"]:
    costs = cost_breakdown.set_index("Resource")[cost_category]
    gendata_mod.loc[costs.index,cost_category] = costs

# this is a hack to get the region and Resource columns back to the order they started in
gendata_mod.reset_index(inplace=True)
gendata_mod.set_index(["region","Resource"],inplace=True)
gendata_mod.reset_index(inplace=True)

#### create variability data

generators_variability = pd.read_csv(case_folder / "Generators_variability.csv").set_index("Time_Index")

hybrid_pv_resources = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Resource"]
hybrid_wind_resources = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_wind","Resource"]

variability_pv = generators_variability[hybrid_pv_resources].reset_index()
variability_wind = generators_variability[hybrid_wind_resources].reset_index()

#### export results

generators_data.to_csv(case_folder / "Generators_data_before_vrestor.csv",index=False)
vrestor_data.to_csv(case_folder / "Vre_and_storage_data.csv",index=False)
gendata_mod.to_csv(case_folder / "Generators_data.csv",index=False)
variability_pv.to_csv(case_folder / "Vre_and_stor_solar_variability.csv",index=False)
variability_wind.to_csv(case_folder / "Vre_and_stor_wind_variability.csv",index=False)