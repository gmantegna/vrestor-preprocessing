import pandas as pd
import numpy as np
import os
path = os.getcwd()
from pathlib import Path
import pathlib

def convert_case_to_vrestor(case_folder: pathlib.PurePath, storage_type: str, colocated_on: bool, zero_out_storage_costs: bool, itc_stor: bool) -> None:
    """ Function to convert a GenX case for use with the VREStor module. If colocated_on is set to
    True, then utility scale PV and onshore wind resources will be converted to VREStor resources,
    and given the option of adding colocated storage. If it is set to False, then these resources will
    still be converted to VREStor resources, but will not be given the option of colocated stoarge. In
    both cases, standalone storage will also be converted to a VREStor resource. The type of storage
    that is affected by this code is controlled by the storage_type parameter.

    Note that this code modifies Generators_data.csv in place, but saves the original Generators_data.csv file as 
    Generators_data_before_vrestor.csv. If the latter file exists, the code will use it as an input, to avoid
    running the code on the wrong inputs.


    NOTE: currently, the storage cost functionality (i.e. if zero_out_storage_costs is set to False)
    is only functional for the Battery storage type and not for LDES.

    Args:
        case_folder (pathlib.PurePath): Pathlib object with the case folder to convert
        storage_type (str): either "LDES" or "Battery"
        colocated_on (bool): set to True if utility scale PV + onshore wind VRESTOR resources should be given colocated storage
        zero_out_storage_costs (bool): set to True if user wishes to set storage costs (for the given storage type) to zero

    Raises:
        ValueError: if an invalid storage type is given
    
    Returns:
        None (case folder is modified in place)
    """
    fom_cost_allocation = {
        "pv":0.87,
        "inverter":0.13
        "gcc":0
    }

    pv_dc_ac_cost_ratio = 0.728
    stor_dc_ac_cost_ratio = 0.945

    # For IRA tax credits
    if itc_stor==True:
        stor_itc = 0.649
    else:
        stor_itc = 1

    ### NEED TO CALCULATE OUTSIDE THIS SHEET: INVERTER AVERAGE COST OVER PLANNING PERIOD
    inv_cost_capex = 132508

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
        power_to_energy_ratio = 0.2375
    else:
        raise ValueError("not a valid storage type")

    #### get cost breakdown and store as "output" df

    if os.path.exists(case_folder / "Generators_data_before_vrestor.csv"):
        generators_data = pd.read_csv(case_folder / "Generators_data_before_vrestor.csv")
    else:
        generators_data = pd.read_csv(case_folder / "Generators_data.csv")
    generators_data["R_ID"] = generators_data.index + 1

    output = pd.DataFrame()

    # get DC costs based on difference between current cost and cost in generators_data

    pv_generators = generators_data[generators_data.technology.str.contains("UtilityPV")].copy(deep=True)
    pv_inv_cost_ac = pv_generators.capex_mw
    pv_inv_cost_dc = pv_inv_cost_ac * pv_dc_ac_cost_ratio # DC dropped values for year

    storage_generators = generators_data[generators_data.technology.str.contains(storage_tech_str)].copy(deep=True)
    storage_capex_mwh_ac = storage_generators.capex_mwh.iloc[0] + storage_generators.capex_mw.iloc[0]/(1/power_to_energy_ratio)
    storage_capex_mwh_dc = storage_capex_mwh_ac * stor_dc_ac_cost_ratio
    storage_capex_mwh_dc_itc = storage_capex_mwh_dc * stor_itc


    # make hybrid pv resources

    hybrid_pv = pv_generators[["region","Resource","technology"]].copy(deep=True)
    hybrid_pv.technology = "hybrid_pv"
    storage_financial_parameters = storage_generators[["region","wacc_real","cap_recovery_years","regional_cost_multiplier"]].rename(columns={
        "wacc_real":"storage_wacc_real",
        "cap_recovery_years":"storage_cap_recovery_years",
        "regional_cost_multiplier":"storage_regional_cost_multiplier"
    }) 
    index_before = pv_generators.index
    pv_generators = pd.merge(pv_generators,storage_financial_parameters,on="region")
    pv_generators.index = index_before

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

    hybrid_pv["Inv_Cost_per_MWyr"] = pv_generators["interconnect_annuity"]
    hybrid_pv["Inv_Cost_Solar_per_MWyr"] = pv_inv_cost_dc * pv_generators["regional_cost_multiplier"] * crf
    hybrid_pv["Inv_Cost_Inverter_per_MWyr"] = inv_cost_capex * pv_generators["storage_regional_cost_multiplier"] * crf_storage * stor_itc
    hybrid_pv["Inv_Cost_Wind_per_MWyr"] = 0
    if zero_out_storage_costs:
        hybrid_pv["Inv_Cost_per_MWhyr"] = 0
    else:
        hybrid_pv["Inv_Cost_per_MWhyr"] = storage_capex_mwh_dc_itc * pv_generators["storage_regional_cost_multiplier"] * crf_storage


    hybrid_pv["Fixed_OM_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["gcc"]
    hybrid_pv["Fixed_OM_Solar_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["pv"]
    hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"] = pv_generators["Fixed_OM_Cost_per_MWyr"] * fom_cost_allocation["inverter"]
    hybrid_pv["Fixed_OM_Wind_Cost_per_MWyr"] = 0
    if zero_out_storage_costs:
        hybrid_pv["Fixed_OM_Cost_per_MWhyr"] = 0
    else:
        hybrid_pv["Fixed_OM_Cost_per_MWhyr"] = storage_capex_mwh_dc * 0.025

    output = pd.concat([output,hybrid_pv],axis=0)

    # make hybrid wind resources

    wind_generators = generators_data[generators_data.technology.str.contains("LandbasedWind")].copy(deep=True)
    hybrid_wind = wind_generators[["region","Resource","technology"]].copy(deep=True)
    hybrid_wind.technology = "hybrid_wind"
    storage_financial_parameters = storage_generators[["region","wacc_real","cap_recovery_years","regional_cost_multiplier"]].rename(columns={
        "wacc_real":"storage_wacc_real",
        "cap_recovery_years":"storage_cap_recovery_years",
        "regional_cost_multiplier":"storage_regional_cost_multiplier"
    })
    index_before = wind_generators.index
    wind_generators = pd.merge(wind_generators,storage_financial_parameters,on="region")
    wind_generators.index = index_before

    crf_storage = (
        np.exp(wind_generators.storage_wacc_real*wind_generators.storage_cap_recovery_years)
        *(np.exp(wind_generators.storage_wacc_real)-1)
    )/(
        np.exp(wind_generators.storage_wacc_real*wind_generators.storage_cap_recovery_years)-1
    )

    hybrid_wind["Inv_Cost_per_MWyr"] = wind_generators["interconnect_annuity"]
    hybrid_wind["Inv_Cost_Wind_per_MWyr"] = wind_generators["Inv_Cost_per_MWyr"] - wind_generators["interconnect_annuity"]
    hybrid_wind["Inv_Cost_Inverter_per_MWyr"] = inv_cost_capex * wind_generators["storage_regional_cost_multiplier"] * crf_storage * stor_itc
    hybrid_wind["Inv_Cost_Solar_per_MWyr"] = 0
    if zero_out_storage_costs:
        hybrid_wind["Inv_Cost_per_MWhyr"] = 0
    else:
        hybrid_wind["Inv_Cost_per_MWhyr"] = storage_capex_mwh_dc_itc * wind_generators["storage_regional_cost_multiplier"] * crf_storage

    hybrid_wind["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
    hybrid_wind["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
    hybrid_wind["Fixed_OM_Solar_Cost_per_MWyr"] = 0
    hybrid_wind["Fixed_OM_Wind_Cost_per_MWyr"] = wind_generators["Fixed_OM_Cost_per_MWyr"] - hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
    if zero_out_storage_costs:
        hybrid_wind["Fixed_OM_Cost_per_MWhyr"] = 0
    else:
        hybrid_wind["Fixed_OM_Cost_per_MWhyr"] = storage_capex_mwh_dc * 0.025

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

    standalone_storage["Inv_Cost_per_MWyr"] = storage_generators["spur_inv_mwyr"]
    standalone_storage["Inv_Cost_Inverter_per_MWyr"] = inv_cost_capex * storage_generators["regional_cost_multiplier"] * crf * stor_itc
    standalone_storage["Inv_Cost_Solar_per_MWyr"] = 0
    standalone_storage["Inv_Cost_Wind_per_MWyr"] = 0
    if zero_out_storage_costs:
        standalone_storage["Inv_Cost_per_MWhyr"] = 0
    else:
        standalone_storage["Inv_Cost_per_MWhyr"] = storage_capex_mwh_dc_itc * storage_generators["regional_cost_multiplier"] * crf

    standalone_storage["Fixed_OM_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Cost_per_MWyr"].iloc[0]
    standalone_storage["Fixed_OM_Inverter_Cost_per_MWyr"] = hybrid_pv["Fixed_OM_Inverter_Cost_per_MWyr"].iloc[0]
    standalone_storage["Fixed_OM_Solar_Cost_per_MWyr"] = 0
    standalone_storage["Fixed_OM_Wind_Cost_per_MWyr"] = 0
    if zero_out_storage_costs:
        standalone_storage["Fixed_OM_Cost_per_MWhyr"] = 0
    else:
        standalone_storage["Fixed_OM_Cost_per_MWhyr"] = storage_capex_mwh_dc * 0.025

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

    # transfer any active MinCap constraints to all VREStor resources. Currently assumes that the MinCap constraints are being applied to storage only.
    for mincap_column in vrestor_data.columns[vrestor_data.columns.str.contains("MinCap")]:
        new_mincap_column_name = "MinCapTagStor" + "_" + mincap_column.split("_")[1]
        regions_with_active_mincap = pd.unique(vrestor_data[vrestor_data[mincap_column]==1].region)
        vrestor_data[new_mincap_column_name] = 0
        vrestor_data.loc[vrestor_data.region.isin(regions_with_active_mincap),new_mincap_column_name] = 1
        vrestor_data[mincap_column] = 0
        vrestor_data["MinCapTagSolar" + "_" + mincap_column.split("_")[1]] = 0
        vrestor_data["MinCapTagWind" + "_" + mincap_column.split("_")[1]] = 0

    # transfer any active MaxCap constraints to all VREStor resources. Currently sets the MaxCapTag_MWh_x column to 1 and the regular maxcap column to 0
    for maxcap_column in vrestor_data.columns[vrestor_data.columns.str.contains("MaxCap")]:
        new_maxcap_column_name = "MaxCapTagStor" + "_" + maxcap_column.split("_")[1]
        regions_with_active_maxcap = pd.unique(vrestor_data[vrestor_data[maxcap_column]==1].region)
        vrestor_data[new_maxcap_column_name] = 0
        vrestor_data.loc[vrestor_data.region.isin(regions_with_active_maxcap),new_maxcap_column_name] = 1
        vrestor_data[maxcap_column] = 0
        vrestor_data["MaxCapTagSolar" + "_" + maxcap_column.split("_")[1]] = 0
        vrestor_data["MaxCapTagWind" + "_" + maxcap_column.split("_")[1]] = 0

    for col_name in ["STOR_AC_DISCHARGE","STOR_AC_CHARGE","Existing_Cap_Inverter_MW","Existing_Cap_Solar_MW","Existing_Cap_Wind_MW",
                    "Existing_Cap_Charge_DC_MW","Existing_Cap_Charge_AC_MW","Existing_Cap_Discharge_DC_MW","Existing_Cap_Discharge_AC_MW",
                    "Min_Cap_Inverter_MW","Min_Cap_Charge_AC_MW","Min_Cap_Discharge_AC_MW","Min_Cap_Charge_DC_MW","Min_Cap_Discharge_DC_MW","Min_Cap_Solar_MW","Min_Cap_Wind_MW",
                    "Inv_Cost_Discharge_DC_per_MWyr","Inv_Cost_Charge_DC_per_MWyr","Inv_Cost_Discharge_AC_per_MWyr","Inv_Cost_Charge_AC_per_MWyr",
                    "Fixed_OM_Cost_Discharge_DC_per_MWyr","Fixed_OM_Cost_Charge_DC_per_MWyr","Fixed_OM_Cost_Discharge_AC_per_MWyr","Fixed_OM_Cost_Charge_AC_per_MWyr",
                    "Var_OM_Cost_per_MWh_Solar","Var_OM_Cost_per_MWh_Wind","Var_OM_Cost_per_MWh_Charge_AC","Var_OM_Cost_per_MWh_Discharge_AC"]:
        vrestor_data[col_name] = 0
    for col_name in ["Max_Cap_Inverter_MW","Max_Cap_Charge_AC_MW","Max_Cap_Discharge_AC_MW","Max_Cap_Charge_DC_MW","Max_Cap_Discharge_DC_MW",
                    "Max_Cap_Solar_MW","Max_Cap_Wind_MW","Inverter_Ratio_Wind","Inverter_Ratio_Solar"]:
        vrestor_data[col_name] = -1

    vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Max_Cap_Solar_MW"] = vrestor_data.loc[vrestor_data.Resource_Type=="hybrid_pv","Max_Cap_MW"] * 1.3
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

    vrestor_data.rename(columns={"LDS":"LDS_VRE_STOR"},inplace=True)

    if storage_type == "LDES":
        vrestor_data["LDS_VRE_STOR"] = 1

    for capres_column in vrestor_data.columns[vrestor_data.columns.str.contains("CapRes")]:
        components = capres_column.split("_")
        new_name = components[0] + "VreStor" + "_" + components[1]
        vrestor_data[capres_column] = vrestor_data[capres_column] * (0.95/0.8)
        vrestor_data.rename(columns={capres_column:new_name},inplace=True)

    for esr_column in vrestor_data.columns[vrestor_data.columns.str.contains("ESR")]:
        components = esr_column.split("_")
        new_name = components[0] + "VreStor" + "_" + components[1]
        vrestor_data.rename(columns={esr_column:new_name},inplace=True)

    if not colocated_on:
        vrestor_data.loc[vrestor_data.Resource_Type != "standalone_storage","STOR_DC_DISCHARGE"] = 0
        vrestor_data.loc[vrestor_data.Resource_Type != "standalone_storage","STOR_DC_CHARGE"] = 0
        vrestor_data.loc[vrestor_data.Resource_Type != "standalone_storage","LDS_VRE_STOR"] = 0

    #### modify generators_data

    gendata_mod = generators_data.copy(deep=True)
    vrestor_resources = vrestor_data.Resource
    print(vrestor_resources)
    pv_and_wind_vrestor_resources = vrestor_data.Resource[vrestor_data.Resource_Type != "standalone_storage"]

    # reset relevant columns
    for capres_column in gendata_mod.columns[gendata_mod.columns.str.contains("CapRes")]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),capres_column] = 0
    for mincap_column in gendata_mod.columns[gendata_mod.columns.str.contains("MinCap")]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),mincap_column] = 0
    for maxcap_column in gendata_mod.columns[gendata_mod.columns.str.contains("MaxCap")]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),maxcap_column] = 0
    for esr_column in gendata_mod.columns[gendata_mod.columns.str.contains("ESR")]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),esr_column] = 0
    for col_name in ["VRE","STOR","Var_OM_Cost_per_MWh_In","Eff_Up","Eff_Down","Min_Duration","Max_Duration","Ramp_Up_Percentage","Ramp_Dn_Percentage","Num_VRE_Bins","LDS"]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),col_name] = 0
    for col_name in ["Var_OM_Cost_per_MWh"]:
        gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),col_name] = 0.15
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"Max_Cap_MW"] = -1
    gendata_mod.loc[gendata_mod.Resource.isin(vrestor_resources),"Max_Cap_MWh"] = -1
    if not colocated_on:
        gendata_mod.loc[gendata_mod.Resource.isin(pv_and_wind_vrestor_resources),"Max_Cap_MWh"] = 0
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

    vrestor_data = vrestor_data.drop(columns=["Num_VRE_Bins", "VRE", "THERM", "MUST_RUN", "STOR", "FLEX", "HYDRO", "VRE_STOR", "Min_Share", "Max_Share", "Existing_Cap_MWh", "Existing_Cap_MW", "Existing_Charge_Cap_MW", "num_units", "unmodified_existing_cap_mw", "New_Build", "Cap_Size", "Min_Cap_MW", "Max_Cap_MW", "Max_Cap_MWh", "Min_Cap_MWh", "Max_Charge_Cap_MW", "Min_Charge_Cap_MW", "Min_Share_percent", "Max_Share_percent","capex_mw", "Inv_Cost_per_MWyr_x", "Inv_Cost_per_MWyr_y", "Fixed_OM_Cost_per_MWyr_x", "Fixed_OM_Cost_per_MWyr_y", "capex_mwh", "Inv_Cost_per_MWhyr_x", "Inv_Cost_per_MWhyr_y", "Fixed_OM_Cost_per_MWhyr_x", "Fixed_OM_Cost_per_MWhyr_y","Var_OM_Cost_per_MWh", "Var_OM_Cost_per_MWh_In", "Inv_Cost_Charge_per_MWyr", "Fixed_OM_Cost_Charge_per_MWyr","Start_Cost_per_MW", "Start_Fuel_MMBTU_per_MW", "Heat_Rate_MMBTU_per_MWh", "heat_rate_mmbtu_mwh_iqr", "heat_rate_mmbtu_mwh_std", "Fuel", "Min_Power", "Self_Disch", "Eff_Up", "Eff_Down", "Hydro_Energy_to_Power_Ratio","Ratio_power_to_energy", "Min_Duration", "Max_Duration", "Max_Flexible_Demand_Delay", "Max_Flexible_Demand_Advance", "Flexible_Demand_Energy_Eff", "Ramp_Up_Percentage", "Ramp_Dn_Percentage", "Up_Time", "Down_Time", "NACC_Eff", "NACC_Peak_to_Base", "Reg_Max", "Rsv_Max", "Reg_Cost", "Rsv_Cost", "spur_miles", "spur_capex", "offshore_spur_miles", "offshore_spur_capex", "tx_miles","tx_capex", "interconnect_annuity", "spur_inv_mwyr", "regional_cost_multiplier", "wacc_real", "investment_years", "lcoe", "cap_recovery_years", "cpa_id", "Commit", "Hydro_level"])
    vrestor_data = vrestor_data.round({'Inv_Cost_Solar_per_MWyr': 0, 'Inv_Cost_Wind_per_MWyr': 0, 'Inv_Cost_Inverter_per_MWyr': 0,'Fixed_OM_Solar_Cost_per_MWyr':0, 'Fixed_OM_Wind_Cost_per_MWyr': 0, 'Fixed_OM_Inverter_Cost_per_MWyr':0})
    gendata_mod = gendata_mod.round({'Inv_Cost_per_MWyr': 0, 'Inv_Cost_per_MWhyr': 0, 'Fixed_OM_Cost_per_MWyr':0, 'Fixed_OM_Cost_per_MWhyr': 0})

    generators_data.to_csv(case_folder / "Generators_data_before_vrestor.csv",index=False)
    vrestor_data.to_csv(case_folder / "Vre_and_stor_data.csv",index=False)
    gendata_mod.to_csv(case_folder / "Generators_data.csv",index=False)
    variability_pv.to_csv(case_folder / "Vre_and_stor_solar_variability.csv",index=False)
    variability_wind.to_csv(case_folder / "Vre_and_stor_wind_variability.csv",index=False)

    print("Finished creating VREStor inputs.")


if __name__ == "__main__":
    convert_case_to_vrestor(case_folder=Path("/Users/gabemantegna/Library/CloudStorage/GoogleDrive-gm1710@princeton.edu/Shared drives/ZERO Lab/Projects_by_leader/Gabriel_Mantegna/LDES_2023/modeling/GenX_cases/3zone_5days_vrestorbranch_vrestorwithcolocation"), storage_type="LDES", colocated_on=True, zero_out_storage_costs=True, itc_stor=False)
