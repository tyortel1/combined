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
            if self.prod_rates_all.empty:
                raise ValueError(f"No production rates found for scenario {self.scenario_id}")

            eur_df = self.prod_rates_all.groupby('uwi').agg({
                'q_oil': 'sum',
                'q_gas': 'sum'
            }).reset_index().rename(columns={'q_oil': 'q_oil_eur', 'q_gas': 'q_gas_eur'})

            for _, row in eur_df.iterrows():
                self.db_manager.save_eur_to_model_properties(
                    row['uwi'], 
                    row['q_oil_eur'], 
                    row['q_gas_eur'], 
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

            results = filtered_df.groupby('uwi').agg({
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
                uwi = row['uwi']
                uwi_data = model_data_df[model_data_df['uwi'] == uwi]
                
                if uwi_data.empty:
                    continue
                    
                q_oil_eur = uwi_data['q_oil_eur'].iloc[0]
                q_gas_eur = uwi_data['q_gas_eur'].iloc[0]

                EUR_oil_remaining = self._calculate_remaining(q_oil_eur, row['EFR_oil'])
                EUR_gas_remaining = self._calculate_remaining(q_gas_eur, row['EFR_gas'])

                self.db_manager.update_uwi_revenue_and_efr(
                    uwi,
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

    @staticmethod
    def _calculate_remaining(eur, efr):
        """Calculate remaining percentage with error handling"""
        try:
            return (1 - (eur - efr) / eur) if eur != 0 else 0
        except ZeroDivisionError:
            return 0