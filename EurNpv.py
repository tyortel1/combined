import pandas as pd
from datetime import datetime
from DatabaseManager import DatabaseManager

class EurNpv:
    def __init__(self, db_manager, scenario_id=1):
        self.db_manager = db_manager
        self.scenario_id = scenario_id

    def calculate_eur(self):
        try:
            self.prod_rates_all = self.db_manager.retrieve_prod_rates_all(scenario_id=self.scenario_id)
            print(self.scenario_id)
            if self.prod_rates_all.empty:
                raise ValueError(f"No production rates found for scenario {self.scenario_id}")

            # Retrieve lateral lengths from UWIs table
            lateral_lengths = self.db_manager.retrieve_lateral_lengths()

            eur_df = self.prod_rates_all.groupby('UWI').agg({
                'q_oil': 'sum',
                'q_gas': 'sum'
            }).reset_index().rename(columns={'q_oil': 'q_oil_eur', 'q_gas': 'q_gas_eur'})

            # Merge lateral lengths
            eur_df = eur_df.merge(lateral_lengths, on='UWI', how='left')

            # Normalize EUR values by lateral length
            eur_df['q_oil_eur_normalized'] = eur_df['q_oil_eur'] / eur_df['lateral']
            eur_df['q_gas_eur_normalized'] = eur_df['q_gas_eur'] / eur_df['lateral']

            for _, row in eur_df.iterrows():
                self.db_manager.save_eur_to_model_properties(
                    row['UWI'], 
                    row['q_oil_eur'], 
                    row['q_gas_eur'], 
                    row.get('q_oil_eur_normalized', None),
                    row.get('q_gas_eur_normalized', None),
                    self.scenario_id
                )
            return eur_df
        except Exception as e:
            print(f"Error calculating EUR: {e}")
            return pd.DataFrame()

    def calculate_npv_and_efr(self):
        try:
            self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)
            model_data_df = pd.DataFrame(self.model_data)
            
            today = pd.Timestamp.today().normalize()
            filtered_df = self.prod_rates_all[pd.to_datetime(self.prod_rates_all['date']) >= today]

            results = filtered_df.groupby('UWI').agg({
                'total_revenue': 'sum',
                'discounted_revenue': 'sum',
                'q_oil': 'sum',
                'q_gas': 'sum'
            }).reset_index().rename(columns={
                'total_revenue': 'npv',
                'discounted_revenue': 'npv_discounted',
                'q_oil': 'EFR_oil',
                'q_gas': 'EFR_gas'
            })

            for _, row in results.iterrows():
                UWI = row['UWI']
                UWI_data = model_data_df[model_data_df['UWI'] == UWI]
                
                if UWI_data.empty:
                    continue
                    
                q_oil_eur = UWI_data['q_oil_eur'].iloc[0]
                q_gas_eur = UWI_data['q_gas_eur'].iloc[0]

                EUR_oil_remaining = self._calculate_remaining(q_oil_eur, row['EFR_oil'])
                EUR_gas_remaining = self._calculate_remaining(q_gas_eur, row['EFR_gas'])

                self.db_manager.update_UWI_revenue_and_efr(
                    UWI,
                    row['npv'],
                    row['npv_discounted'],
                    row['EFR_oil'],
                    row['EFR_gas'],
                    EUR_oil_remaining,
                    EUR_gas_remaining,
                    self.scenario_id
                )
            return results
        except Exception as e:
            print(f"Error calculating NPV and EFR: {e}")
            return pd.DataFrame()

    def calculate_payback_months(self):
        try:
            payback_results = []
            for UWI, well_data in self.prod_rates_all.groupby('UWI'):
                capex = self.db_manager.get_capex_for_UWI(UWI, self.scenario_id)
                opex = self.db_manager.get_opex_for_UWI(UWI, self.scenario_id)
                cumulative_revenue = 0
                months = 0
                
                for _, month_data in well_data.sort_values(by='date').iterrows():
                    monthly_revenue = month_data['total_revenue']
                    cumulative_revenue += monthly_revenue - opex
                    months += 1
                    
                    if cumulative_revenue >= capex:
                        break
                else:
                    months = None  # Indicates payback was not reached within the data range
                
                self.db_manager.update_payback_months(UWI, months, self.scenario_id)
                payback_results.append({'UWI': UWI, 'payback_months': months})
            
            payback_df = pd.DataFrame(payback_results)
            return payback_df
        except Exception as e:
            print(f"Error calculating payback months: {e}")
            return pd.DataFrame()

    @staticmethod
    def _calculate_remaining(eur, efr):
        """Calculate remaining percentage with error handling"""
        try:
            return (1 - (eur - efr) / eur) if eur != 0 else 0
        except ZeroDivisionError:
            return 0
