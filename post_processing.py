import pandas as pd
import numpy as np
import os
path = os.getcwd()

# Aneesha code

# MID COST RESOURCES
# List of PV/wind resources
vre_mid = ['LandbasedWind_Class1_Moderate_','UtilityPV_Class1_Moderate_', 'Battery_*_Moderate', 'LandbasedWind_Class1_Advanced_', 'UtilityPV_Class1_Advanced_', 'Battery_*_Advanced']
wind_mid_list = ['LandbasedWind_Class1_Moderate_', 'LandbasedWind_Class1_Advanced_']
pv_mid_list = ['UtilityPV_Class1_Moderate_', 'UtilityPV_Class1_Advanced_']
bat_mid_list = ['Battery_*_Moderate', 'Battery_*_Advanced']
hydro_list = ['Conventional Hydroelectric']

# READ DATA
wecc_data = pd.read_csv(os.path.join(path, "prev_mid.csv"), header='infer', sep=',')
generator = pd.read_csv(os.path.join(path, "Inputs/Generators_data.csv"), header='infer', sep=',')

# Get these PV/wind/battery generators
indices_mid = np.where(generator.technology.isin(vre_mid)) 
indices_pv = np.where(generator.technology.isin(pv_mid_list)) 
indices_wind = np.where(generator.technology.isin(wind_mid_list)) 
mid_vre = generator.loc[generator.technology.isin(vre_mid)]
indices_hydro = np.where(generator.technology.isin(hydro_list)) 
# Get rid of these resources from generator_data.csv
#generator = generator.loc[~generator.technology.isin(vre_mid)]

# Create dataframe
vre_mid_list = pd.DataFrame()
vre_mid_list["region"] = mid_vre["region"]
vre_mid_list["Resource"] = mid_vre["Resource"]
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "technology"] = "hybrid_wind"
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "technology"] = "hybrid_pv"
vre_mid_list.loc[mid_vre.technology.isin(bat_mid_list), "technology"] = "standalone_storage"
vre_mid_list["R_ID"] = mid_vre["R_ID"]
vre_mid_list["Zone"] = mid_vre["Zone"]
vre_mid_list["cluster"] = mid_vre["cluster"] 

vre_mid_list["SOLAR"] = 0
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "SOLAR"] = 1

vre_mid_list["WIND"] = 0
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "WIND"] = 1

vre_mid_list["STOR_DC_DISCHARGE"] = 1
vre_mid_list["STOR_DC_CHARGE"] = 1
vre_mid_list["STOR_AC_DISCHARGE"] = 0
vre_mid_list["STOR_AC_CHARGE"] = 0
vre_mid_list["LDS"] = 0

vre_mid_list["ESR_1"] = mid_vre["ESR_1"]
vre_mid_list["ESR_2"] = mid_vre["ESR_2"]
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "CapRes_1"] = mid_vre["CapRes_1"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "CapRes_2"] = mid_vre["CapRes_2"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "CapRes_3"] = mid_vre["CapRes_3"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "CapRes_1"] = mid_vre["CapRes_1"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "CapRes_2"] = mid_vre["CapRes_2"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "CapRes_3"] = mid_vre["CapRes_3"] * 1.1875
vre_mid_list.loc[mid_vre.technology.isin(bat_mid_list), "CapRes_1"] = mid_vre["CapRes_1"]
vre_mid_list.loc[mid_vre.technology.isin(bat_mid_list), "CapRes_2"] = mid_vre["CapRes_2"]
vre_mid_list.loc[mid_vre.technology.isin(bat_mid_list), "CapRes_3"] = mid_vre["CapRes_3"]

vre_mid_list["Existing_Cap_Inverter_MW"] = 0
vre_mid_list["Existing_Cap_Solar_MW"] = 0
vre_mid_list["Existing_Cap_Wind_MW"] = 0
vre_mid_list["Existing_Cap_Charge_DC_MW"] = 0
vre_mid_list["Existing_Cap_Charge_AC_MW"] = 0
vre_mid_list["Existing_Cap_Discharge_DC_MW"] = 0
vre_mid_list["Existing_Cap_Discharge_AC_MW"] = 0

vre_mid_list["Max_Cap_Inverter_MW"] = -1
vre_mid_list["Min_Cap_Inverter_MW"] = 0
vre_mid_list["Max_Cap_Charge_AC_MW"] = -1
vre_mid_list["Min_Cap_Charge_AC_MW"] = 0
vre_mid_list["Max_Cap_Discharge_AC_MW"] = -1
vre_mid_list["Min_Cap_Discharge_AC_MW"] = 0
vre_mid_list["Max_Cap_Charge_DC_MW"] = -1
vre_mid_list["Min_Cap_Charge_DC_MW"] = 0
vre_mid_list["Max_Cap_Discharge_DC_MW"] = -1
vre_mid_list["Min_Cap_Discharge_DC_MW"] = 0
vre_mid_list["Min_Cap_Solar_MW"] = 0
vre_mid_list["Max_Cap_Solar_MW"] = -1
vre_mid_list["Min_Cap_Wind_MW"] = 0
vre_mid_list["Max_Cap_Wind_MW"] = -1
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "Max_Cap_Wind_MW"] = mid_vre["Max_Cap_MW"]
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "Max_Cap_Solar_MW"] = round(mid_vre["Max_Cap_MW"] * 1.3, 1)

#max_stor = (pd.Series(wecc_data.Max_Cap_Stor_MWh.values,index=wecc_data.Resource)).to_dict()
#vre_mid_list["Max_Cap_Stor_MWh"] = vre_mid_list["Resource"].map(max_stor)

#vre_mid_list["capex_VRE"] = wecc_data["capex_VRE"].values   # will change output post-process
#capex_VRE = (pd.Series(wecc_data.capex_VRE.values,index=wecc_data.Resource)).to_dict()
#vre_mid_list["capex_VRE"] = round(vre_mid_list["Resource"].map(capex_VRE))

#vre_mid_list["Inv_Cost_VRE_per_MWyr"] = wecc_data["Inv_Cost_VRE_per_MWyr"].values # will change output post-process
Inv_Cost_Inverter_per_MWyr = (pd.Series(wecc_data.Inv_Cost_Inverter_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Inv_Cost_Inverter_per_MWyr"] = round(vre_mid_list["Resource"].map(Inv_Cost_Inverter_per_MWyr))

Inv_Cost_Solar_per_MWyr = (pd.Series(wecc_data.Inv_Cost_Solar_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Inv_Cost_Solar_per_MWyr"] = round(vre_mid_list["Resource"].map(Inv_Cost_Solar_per_MWyr))

Inv_Cost_Wind_per_MWyr = (pd.Series(wecc_data.Inv_Cost_Wind_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Inv_Cost_Wind_per_MWyr"] = round(vre_mid_list["Resource"].map(Inv_Cost_Wind_per_MWyr))

vre_mid_list["Inv_Cost_Discharge_DC_per_MWyr"] = 0
vre_mid_list["Inv_Cost_Charge_DC_per_MWyr"] = 0
vre_mid_list["Inv_Cost_Discharge_AC_per_MWyr"] = 0
vre_mid_list["Inv_Cost_Charge_AC_per_MWyr"] = 0

#vre_mid_list["Fixed_OM_VRE_Cost_per_MWyr"] = wecc_data["Fixed_OM_VRE_Cost_per_MWyr"].values # will change output post-process
Fixed_OM_Inverter_Cost_per_MWyr = (pd.Series(wecc_data.Fixed_OM_Inverter_Cost_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Fixed_OM_Inverter_Cost_per_MWyr"] = round(vre_mid_list["Resource"].map(Fixed_OM_Inverter_Cost_per_MWyr))

Fixed_OM_Solar_Cost_per_MWyr = (pd.Series(wecc_data.Fixed_OM_Solar_Cost_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Fixed_OM_Solar_Cost_per_MWyr"] = round(vre_mid_list["Resource"].map(Fixed_OM_Solar_Cost_per_MWyr))

Fixed_OM_Wind_Cost_per_MWyr = (pd.Series(wecc_data.Fixed_OM_Wind_Cost_per_MWyr.values,index=wecc_data.Resource)).to_dict()
vre_mid_list["Fixed_OM_Wind_Cost_per_MWyr"] = round(vre_mid_list["Resource"].map(Fixed_OM_Wind_Cost_per_MWyr))

vre_mid_list["Fixed_OM_Cost_Discharge_DC_per_MWyr"] = 0
vre_mid_list["Fixed_OM_Cost_Charge_DC_per_MWyr"] = 0
vre_mid_list["Fixed_OM_Cost_Discharge_AC_per_MWyr"] = 0
vre_mid_list["Fixed_OM_Cost_Charge_AC_per_MWyr"] = 0

vre_mid_list["Var_OM_Cost_per_MWh_Solar"] = 0
vre_mid_list.loc[mid_vre.technology.isin(pv_mid_list), "Var_OM_Cost_per_MWh_Solar"] = mid_vre["Var_OM_Cost_per_MWh"]
vre_mid_list["Var_OM_Cost_per_MWh_Wind"] = 0
vre_mid_list.loc[mid_vre.technology.isin(wind_mid_list), "Var_OM_Cost_per_MWh_Wind"] = mid_vre["Var_OM_Cost_per_MWh"]
vre_mid_list["Var_OM_Cost_per_MWh_Charge_DC"] = 0.15
vre_mid_list["Var_OM_Cost_per_MWh_Discharge_DC"] = 0.15
vre_mid_list["Var_OM_Cost_per_MWh_Charge_AC"] = 0
vre_mid_list["Var_OM_Cost_per_MWh_Discharge_AC"] = 0

vre_mid_list["Self_Disch"] = 0.05
vre_mid_list["Eff_Up_DC"] = 0.95
vre_mid_list["Eff_Down_DC"] = 0.95
vre_mid_list["Eff_Up_AC"] = 0.95
vre_mid_list["Eff_Down_AC"] = 0.95
vre_mid_list["EtaInverter"] = 0.967
vre_mid_list["Inverter_Ratio_Wind"] = -1
vre_mid_list["Inverter_Ratio_Solar"] = -1
vre_mid_list["C_Rate_DC"] = 0.25
vre_mid_list["C_Rate_AC"] = 0.25
vre_mid_list["spur_line_costs"] = mid_vre["interconnect_annuity"]
vre_mid_list["regional_multipliers"] = mid_vre["regional_cost_multiplier"]

# GENERATORS_DATA.CSV
#nuclear_list = ['nuclear', 'nuclear_mid']
#ng_list = ['natural_gas_fired_combined_cycle', 'natural_gas_fired_combustion_turbine', 'naturalgas_ccavgcf_mid', 'naturalgas_ctavgcf_mid']
#generator.loc[(generator.region == 'CA_N')&(generator.technology.isin(nuclear_list)), 'New_Build'] = 0
#generator.loc[(generator.region == 'CA_S')&(generator.technology.isin(nuclear_list)), 'New_Build'] = 0
generator.loc[generator.technology.isin(vre_mid), "CapRes_1"] = 0
generator.loc[generator.technology.isin(vre_mid), "CapRes_2"] = 0
generator.loc[generator.technology.isin(vre_mid), "CapRes_3"] = 0
generator.loc[generator.technology.isin(vre_mid), "VRE"] = 0
generator.loc[generator.technology.isin(vre_mid), "STOR"] = 0
generator.loc[generator.technology.isin(vre_mid), "ESR_1"] = 0
generator.loc[generator.technology.isin(vre_mid), "ESR_2"] = 0
generator.loc[generator.technology.isin(vre_mid), "Max_Cap_MW"] = -1 
generator.loc[generator.technology.isin(vre_mid), "Max_Cap_MWh"] = -1 
generator.loc[generator.technology.isin(pv_mid_list), "Var_OM_Cost_per_MWh"] = 0 
generator.loc[generator.technology.isin(wind_mid_list), "Var_OM_Cost_per_MWh"] = 0 
generator.loc[generator.technology.isin(pv_mid_list), "Var_OM_Cost_per_MWh_In"] = 0 
generator.loc[generator.technology.isin(wind_mid_list), "Var_OM_Cost_per_MWh_In"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Var_OM_Cost_per_MWh"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Var_OM_Cost_per_MWh_In"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Eff_Up"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Eff_Down"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Min_Duration"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Max_Duration"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Ramp_Up_Percentage"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Ramp_Dn_Percentage"] = 0 
generator.loc[generator.technology.isin(bat_mid_list), "Max_Duration"] = 0 
generator.loc[generator.technology.isin(vre_mid), "Self_Disch"] = 0.05 
generator.loc[generator.technology.isin(vre_mid), "Commit"] = 0
generator.loc[generator.technology.isin(vre_mid), "Num_VRE_Bins"] = 0
generator.loc[generator.technology.isin(vre_mid), "VRE_STOR"] = 1

Inv_Cost_per_MWyr = (pd.Series(wecc_data.Inv_Cost_per_MWyr.values,index=wecc_data.Resource)).to_dict()
generator.loc[generator.technology.isin(vre_mid), "Inv_Cost_per_MWyr"] = round(vre_mid_list["Resource"].map(Inv_Cost_per_MWyr))

Fixed_OM_Cost_per_MWyr = (pd.Series(wecc_data.Fixed_OM_Cost_per_MWyr.values,index=wecc_data.Resource)).to_dict()
generator.loc[generator.technology.isin(vre_mid), "Fixed_OM_Cost_per_MWyr"] = round(vre_mid_list["Resource"].map(Fixed_OM_Cost_per_MWyr))

Inv_Cost_per_MWhyr = (pd.Series(wecc_data.Inv_Cost_per_MWhyr.values,index=wecc_data.Resource)).to_dict()
generator.loc[generator.technology.isin(vre_mid), "Inv_Cost_per_MWhyr"] = round(vre_mid_list["Resource"].map(Inv_Cost_per_MWhyr))

Fixed_OM_Cost_per_MWhyr = (pd.Series(wecc_data.Fixed_OM_Cost_per_MWhyr.values,index=wecc_data.Resource)).to_dict()
generator.loc[generator.technology.isin(vre_mid), "Fixed_OM_Cost_per_MWhyr"] = round(vre_mid_list["Resource"].map(Fixed_OM_Cost_per_MWhyr))


#generator.loc[(generator.technology == 'Nuclear'), 'New_Build'] = -1 # ask jesse
#generator.loc[generator.technology == 'naturalgas_ccs100_mid', 'New_Build'] = 0
#generator["Flexible_Demand_Energy_Eff"] = 1
#generator["Rsv_Cost"] = 0
#generator["Reg_Cost"] = 0

#generator.loc[(generator.region == 'WECC_NMAZ')&(generator.technology.isin(ng_list)), 'Fuel'] = "nmaz_naturalgas"
#generator.loc[(generator.region == 'WECC_NMAZ')&(generator.technology == 'naturalgas_ccccsavgcf_mid'), 'Fuel'] = "nmaz_naturalgas_ccs90"
#generator.loc[(generator.region == 'WECC_NMAZ')&(generator.technology == 'naturalgas_ccs100_mid'), 'Fuel'] = "nmaz_naturalgas_ccs100" 

# GENERATORS VARIABILITY
gen_var = pd.read_csv(os.path.join(path, "Inputs/Generators_variability.csv"), header='infer', sep=',')
indices_mid = [x+1 for x in indices_mid]
indices_pv = [x+1 for x in indices_pv]
indices_wind = [x+1 for x in indices_wind]
#indices_hydro = [x+1 for x in indices_hydro]
#hydro_mins = gen_var.iloc[:,indices_hydro[0]].min()
#print(hydro_mins.shape)
#generator.loc[(generator.Resource == 'CA_N_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[0]-0.01
#generator.loc[(generator.Resource == 'CA_S_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[1]-0.01
#generator.loc[(generator.Resource == 'WECC_N_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[2]-0.01
#generator.loc[(generator.Resource == 'WECC_NMAZ_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[3]-0.01
#generator.loc[(generator.Resource == 'WECC_PNW_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[4]-0.01
#generator.loc[(generator.Resource == 'WECC_PNW_conventional_hydroelectric_1'), 'Min_Power'] = hydro_mins[5]-0.01

#gen_var.iloc[:,indices_pv[0]] = gen_var.iloc[:,indices_pv[0]] / 0.9 / 1.34
pv_variability = round(gen_var.iloc[:,indices_pv[0]], 5)
pv_variability.insert(loc=0, column='Time_Index', value=gen_var.iloc[:,0])
pv_variability.to_csv(os.path.join(path, "Inputs/Vre_and_stor_solar_variability.csv"),encoding='utf-8',index=False)

wind_variability = round(gen_var.iloc[:,indices_wind[0]], 5)
wind_variability.insert(loc=0, column='Time_Index', value=gen_var.iloc[:,0])
wind_variability.to_csv(os.path.join(path, "Inputs/Vre_and_stor_wind_variability.csv"),encoding='utf-8',index=False)

generator.to_csv(os.path.join(path, "Inputs/new_generators_data.csv"),encoding='utf-8',index=False)
#vre_mid_list = vre_mid_list.sort_values(["technology", "region"], ascending = (True, True))
vre_mid_list.to_csv(os.path.join(path, "Inputs/Vre_and_storage_data.csv"),encoding='utf-8',index=False)

#gen_var = gen_var.drop(gen_var.iloc[:,indices_mid[0]], axis = 1)
#gen_var = round(gen_var, 5)
#gen_var.to_csv(os.path.join(path, "Inputs/new_generators_variability.csv"),encoding='utf-8',index=False)
    