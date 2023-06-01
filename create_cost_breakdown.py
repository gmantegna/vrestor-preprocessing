import pandas as pd
import numpy as np
import os
# import yaml
# from IPython import embed as IP
path = os.getcwd()
from pathlib import Path


# parameters
y = 2045
case_folder = Path("./sample_case_with_LDES")
fom_cost_allocation = {
    "pv":0.63,
    "gcc":0.1,
    "inverter":0.27
}

cur_pv_cost_per_mw_ac = 1309972
cur_storage_cost_per_mwh_ac = 424189

cur_pv_cost_per_mw_dc = 811187
cur_storage_cost_per_mwh_dc = 405377
cur_inverter_cost_per_mw_ac = 132508

standalone_battery_gcc = 2560 #annuitized interconnection fee in 2022$

generators_data = pd.read_csv(case_folder / "Generators_data.csv")

# get DC costs based on difference between current cost and cost in generators_data

pv_generators = generators_data[generators_data.technology.str.contains("UtilityPV")].copy(deep=True)
pv_capex_mw_future = pv_generators.capex_mw.iloc[0]
pv_cost_decrease_ratio = pv_capex_mw_future / cur_pv_cost_per_mw_ac
pv_cost_per_mw_dc = cur_pv_cost_per_mw_dc * pv_cost_decrease_ratio
inverter_cost_per_mw_ac = cur_inverter_cost_per_mw_ac * pv_cost_decrease_ratio

storage_generators = generators_data[generators_data.technology.str.contains("Battery")].copy(deep=True)
storage_capex_mwh_future = storage_generators.capex_mwh.iloc[0] + storage_generators.capex_mw.iloc[0]/4
storage_cost_decrease_ratio = storage_capex_mwh_future / cur_storage_cost_per_mwh_ac
storage_cost_per_mwh_dc = cur_storage_cost_per_mwh_dc * storage_cost_decrease_ratio

# result: pv_cost_per_mw_dc, inverter_cost_per_mw_ac, storage_cost_per_mwh_dc

output = pd.DataFrame()

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

hybrid_pv["Inv_Cost_Inverter_per_MWyr"] = inverter_cost_per_mw_ac * pv_generators["regional_cost_multiplier"] * crf_storage
hybrid_pv["Inv_Cost_Solar_per_MWyr"] = pv_cost_per_mw_dc * pv_generators["regional_cost_multiplier"] * crf
hybrid_pv["Inv_Cost_Wind_per_MWyr"] = 0

hybrid_pv["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * pv_generators["storage_regional_cost_multiplier"] * crf_storage
hybrid_pv["Fixed_OM_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["gcc"]
hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["inverter"]
hybrid_pv["Fixed_OM_Solar_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["pv"]
hybrid_pv["Fixed_OM_Wind_Cost_per_MWyr"] = 0
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
hybrid_wind["Inv_Cost_Inverter_per_MWyr"] = inverter_cost_per_mw_ac * wind_generators["regional_cost_multiplier"] * crf_storage
hybrid_wind["Inv_Cost_Solar_per_MWyr"] = 0
hybrid_wind["Inv_Cost_Wind_per_MWyr"] = wind_generators["Inv_Cost_per_MWyr"] - wind_generators["interconnect_annuity"]
hybrid_wind["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * wind_generators["storage_regional_cost_multiplier"] * crf_storage


## NOTE: currently assuming FOM for GCC and inverter for hybrid wind are the same as for hybrid pv.
hybrid_wind["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
hybrid_wind["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
hybrid_wind["Fixed_OM_Solar_Cost_per_MWyr"] = 0
hybrid_wind["Fixed_OM_Wind_Cost_per_MWyr"] = wind_generators["Fixed_OM_Cost_per_MWyr"] - hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
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
standalone_storage["Inv_Cost_per_MWhyr"] = storage_cost_per_mwh_dc * storage_generators["regional_cost_multiplier"] * crf

# once again assuming FOM for GCC and inverter are same as for hybrid pv
standalone_storage["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
standalone_storage["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
standalone_storage["Fixed_OM_Solar_Cost_per_MWyr"] = 0
standalone_storage["Fixed_OM_Wind_Cost_per_MWyr"] = 0
standalone_storage["Fixed_OM_Cost_per_MWhyr"] = storage_generators["Fixed_OM_Cost_per_MWhyr"]

output = pd.concat([output,standalone_storage],axis=0)

output.to_csv("cost_breakdown.csv",index=False)