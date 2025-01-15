import pandas as pd
from datetime import datetime
from DatabaseManager import DatabaseManager

class EurNpv:
    def __init__(self, db_manager, db_path):
        self.db_manager = db_manager
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)


    def calculate_eur(self):
        # Retrieve production rates from the database
       
        self.prod_rates_all = self.db_manager.retrieve_prod_rates_all()
        print()
        # Group by UWI and sum the production columns
        eur_df = self.prod_rates_all.groupby('uwi').agg(
            q_oil_eur=('q_oil', 'sum'),  # Sum of oil production
            q_gas_eur=('q_gas', 'sum')  # Sum of gas production
        ).reset_index()

        scenario_id = 1

        # Insert the EUR values for each UWI into the database or display
        for _, row in eur_df.iterrows():
            uwi = row['uwi']
            q_oil_eur = row['q_oil_eur']
            q_gas_eur = row['q_gas_eur']
            # Print or log EUR values
            print(f"UWI: {uwi}, Q_Oil_EUR: {q_oil_eur}, Q_Gas_EUR: {q_gas_eur}")
            # Update the database
            self.db_manager.save_eur_to_model_properties(uwi, q_oil_eur, q_gas_eur, scenario_id)

    def calculate_npv_and_efr(self):
        self.model_data = self.db_manager.retrieve_model_data()
        model_data_df = pd.DataFrame(self.model_data)

        # Get today's date
        today = datetime.today().strftime('%Y-%m-%d')

        # Filter the DataFrame for dates >= today's date
        filtered_df = self.prod_rates_all[self.prod_rates_all['date'] >= today]

        # Group by UWI and calculate NPV, discounted NPV, EFR_gas, and EFR_oil
        results = filtered_df.groupby('uwi').agg(
            npv=('total_revenue', 'sum'),
            npv_discounted=('discounted_revenue', 'sum'),
            EFR_oil=('q_oil', 'sum'),  # Sum q_oil for oil
            EFR_gas=('q_gas', 'sum')  # Sum q_gas for gas
        ).reset_index()

        # Insert the results for each UWI into the database
        for _, row in results.iterrows():
            uwi = row['uwi']
            npv = row['npv']
            npv_discounted = row['npv_discounted']
            EFR_oil = row['EFR_oil']
            EFR_gas = row['EFR_gas']

            # Grab q_oil_eur and q_gas_eur from self.model_data for the UWI
            q_oil_eur = model_data_df.loc[model_data_df['uwi'] == uwi, 'q_oil_eur'].values[0]
            q_gas_eur = model_data_df.loc[model_data_df['uwi'] == uwi, 'q_gas_eur'].values[0]

            # Subtract the EUR values from EFR values and calculate percentage remaining
            EUR_oil_remaining = (1 - (q_oil_eur - EFR_oil) / q_oil_eur) if q_oil_eur != 0 else 0
            EUR_gas_remaining = (1- (q_gas_eur - EFR_gas) / q_gas_eur) if q_gas_eur != 0 else 0

            print(f"UWI: {uwi}, NPV: {npv}, NPV Discounted: {npv_discounted}, EFR Oil: {EFR_oil}, EFR Gas: {EFR_gas}")
            print(f"EUR Oil Remaining: {EUR_oil_remaining*100:.2f}%, EUR Gas Remaining: {EUR_gas_remaining*100:.2f}%")

            # Update the database with the calculated values and the remaining EUR percentages
            scenario = 1  # You can adjust this value as needed

            self.db_manager.update_uwi_revenue_and_efr(
                uwi, npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, scenario
            )
