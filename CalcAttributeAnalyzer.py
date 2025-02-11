from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QSplitter,
                               QWidget, QLineEdit, QAbstractItemView, QPushButton, 
                               QListWidget, QMessageBox, QFileDialog, QComboBox, 
                               QGroupBox, QCheckBox, QSpinBox, QTabWidget, QSizePolicy)

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDoubleValidator
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import PatternFill
import numpy as np
import traceback
import pingouin as pg
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error





class CalcAttributeAnalyzer(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Well Zone Correlation Analysis")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)
        
        main_layout = QVBoxLayout()
        
        regression_group = QGroupBox("Regression Selection")
        regression_layout = QVBoxLayout()

        # Create horizontal layout for regression selection
        regression_row = QHBoxLayout()
        regression_label = QLabel("Select Regression:")
        regression_label.setFixedWidth(144)  # 1.5 inches at 96 DPI
        regression_row.addWidget(regression_label)

        # Regression combo box
        self.regression_combo = QComboBox()
        self.regression_combo.setFixedWidth(144)
        self.regression_combo.addItem("")
        self.regression_combo.setCurrentText("")
        self.regression_combo.currentIndexChanged.connect(self.regression_changed)
        regression_row.addWidget(self.regression_combo)
        regression_row.addStretch()
        regression_layout.addLayout(regression_row)

        # Create horizontal layout for target variable selection
        target_row = QHBoxLayout()
        target_label = QLabel("Target Variable:")
        target_label.setFixedWidth(144)
        target_row.addWidget(target_label)

        # Target variable combo box
        self.target_combo = QComboBox()
        self.target_combo.setFixedWidth(144)
        self.target_combo.addItem("")
        self.target_combo.setCurrentText("")
        target_row.addWidget(self.target_combo)
        target_row.addStretch()
        regression_layout.addLayout(target_row)

        # Description row
        description_row = QHBoxLayout()
        description_label = QLabel("Description:")
        description_label.setFixedWidth(144)
        description_row.addWidget(description_label)

        self.regression_description = QLabel()
        self.regression_description.setWordWrap(False)  # Changed to False to allow horizontal expansion
        self.regression_description.setText("")
        self.regression_description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Allow horizontal expansion
        description_row.addWidget(self.regression_description)
        regression_layout.addLayout(description_row)

        regression_group.setLayout(regression_layout)
        main_layout.addWidget(regression_group)
        
        # Analysis Settings
        settings_group = QGroupBox("Analysis Settings")
        settings_layout = QHBoxLayout()
        
        # Statistical Method Selection
        stats_layout = QVBoxLayout()
        stats_layout.addWidget(QLabel("Statistical Method:"))
        self.stats_combo = QComboBox()
        self.stats_combo.addItems(["Pearson", "Spearman", "Kendall"])
        stats_layout.addWidget(self.stats_combo)
        settings_layout.addLayout(stats_layout)
        
        # Correlation Threshold Input
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(QLabel("Correlation Threshold:"))
        self.threshold_input = QLineEdit()
        self.threshold_input.setValidator(QDoubleValidator(0.0, 1.0, 2))
        self.threshold_input.setText("0.7")
        threshold_layout.addWidget(self.threshold_input)
        settings_layout.addLayout(threshold_layout)
        
        # Minimum Valid Data Input
        min_valid_data_layout = QVBoxLayout()
        min_valid_data_layout.addWidget(QLabel("Min % of Valid Data (before dropping columns):"))
        self.min_valid_data_input = QSpinBox()
        self.min_valid_data_input.setRange(10, 100)  # Min 10%, Max 100%
        self.min_valid_data_input.setValue(50)  # Default to 50%
        self.min_valid_data_input.setSuffix("%")  # Show % in UI
        min_valid_data_layout.addWidget(self.min_valid_data_input)
        settings_layout.addLayout(min_valid_data_layout)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # UWI Selection
        UWI_group = QGroupBox("Well Selection")
        UWI_layout = QVBoxLayout()
        
        UWI_search = QLineEdit()
        UWI_search.setPlaceholderText("Search UWIs...")
        UWI_search.textChanged.connect(self.filter_UWIs)
        UWI_layout.addWidget(UWI_search)
        
        UWI_lists = QHBoxLayout()
        self.available_UWIs = QListWidget()
        self.available_UWIs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_UWIs = QListWidget()
        self.selected_UWIs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        UWI_buttons = QVBoxLayout()
        btn_select_UWI = QPushButton(">")
        btn_deselect_UWI = QPushButton("<")
        btn_select_all_UWI = QPushButton(">>")
        btn_deselect_all_UWI = QPushButton("<<")
        
        btn_select_UWI.clicked.connect(self.select_UWI)
        btn_deselect_UWI.clicked.connect(self.deselect_UWI)
        btn_select_all_UWI.clicked.connect(self.select_all_UWIs)
        btn_deselect_all_UWI.clicked.connect(self.deselect_all_UWIs)
        
        UWI_buttons.addWidget(btn_select_all_UWI)
        UWI_buttons.addWidget(btn_select_UWI)
        UWI_buttons.addWidget(btn_deselect_UWI)
        UWI_buttons.addWidget(btn_deselect_all_UWI)
        
        UWI_lists.addWidget(QLabel("Available UWIs"))
        UWI_lists.addWidget(self.available_UWIs)
        UWI_lists.addLayout(UWI_buttons)
        UWI_lists.addWidget(QLabel("Selected UWIs"))
        UWI_lists.addWidget(self.selected_UWIs)
        UWI_layout.addLayout(UWI_lists)
        UWI_group.setLayout(UWI_layout)
        main_layout.addWidget(UWI_group)
        
        # Run Button
        btn_run = QPushButton("Run Analysis")
        btn_run.clicked.connect(self.run_analysis)
        main_layout.addWidget(btn_run)
        
        self.setLayout(main_layout)
        self.load_data()

    def regression_changed(self, index):
        """Handle regression selection change"""
        print(f"Regression changed to index: {index}")  # Debug print
        self.update_regression_description(index)
        self.update_target_variables(index)  # Pass the index here

    def update_regression_description(self, index):
        """Update the description text when a regression is selected"""
        description = self.regression_combo.itemData(index)
        self.regression_description.setText(description if description else "No description available")

    def update_target_variables(self, index):  # Keep the index parameter
        """Update target variables dropdown when regression table is selected"""
        selected_regression = self.regression_combo.currentText()
        print(f"Updating target variables for: {selected_regression}")  # Debug print
        if selected_regression:
            target_variables = self.db_manager.get_unique_attributes(selected_regression)
            print(f"Found target variables: {target_variables}")  # Debug print
            self.target_combo.clear()
            if target_variables:
                self.target_combo.addItems(target_variables)
    def load_data(self):
        """Load available UWIs and regression tables from the database"""
        try:
            # Load UWIs
            UWIs = self.db_manager.get_UWIs()
            self.available_UWIs.addItems(UWIs)
        
            # Load regression tables
            regression_tables = self.db_manager.get_regression_tables()
            print(regression_tables)
            self.regression_combo.clear()
            for table, description in regression_tables:
                self.regression_combo.addItem(table, description)  # Store description as user data
        
            # Update description and target variables for first item
            if regression_tables:
                self.update_regression_description(0)
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")
    def update_regression_description(self, index):
        """Update the description text when a regression is selected"""
        description = self.regression_combo.itemData(index)
        if description:
            self.regression_description.setText(description)
        else:
            self.regression_description.setText("No description available")




    def run_analysis(self):
        """Run multiple regression analyses and compare their performance."""
        try:
            # Get selected UWIs
            UWIs = [self.selected_UWIs.item(i).text() for i in range(self.selected_UWIs.count())]
            if not UWIs:
                QMessageBox.warning(self, "Invalid Selection", "Please select at least one UWI")
                return

            # Get selected regression table and target variable
            selected_regression = self.regression_combo.currentText()
            target_variable = self.target_combo.currentText()
            if not selected_regression or not target_variable:
                QMessageBox.warning(self, "Invalid Selection", "Please select both regression table and target variable")
                return

            # Get regression data
            regression_data = self.db_manager.get_regression_data(selected_regression, UWIs)
            print(regression_data)
            if regression_data is None or regression_data.empty:
                QMessageBox.warning(self, "No Data", "No data found for the selected regression and UWIs")
                return

            # Prepare the data
            # Pivot the data to get features as columns
            data_pivoted = regression_data.pivot(
                index='UWI',
                columns='attribute_name',
                values='attribute_value'
            ).reset_index()

            if target_variable not in data_pivoted.columns:
                QMessageBox.warning(self, "Invalid Selection", f"Target variable {target_variable} not found in data")
                return



            # Separate features and target
            X = data_pivoted.drop([target_variable, 'UWI'], axis=1)
            y = data_pivoted[target_variable]

            # Check for NaN values and print affected UWIs
            print("\n🔍 Checking for NaN values in X before training:")
            nan_counts = X.isna().sum()
            nan_columns = nan_counts[nan_counts > 0]  # Get only columns with NaNs

            if not nan_columns.empty:
                print(f"⚠️ NaNs detected in columns: {nan_columns.index.tolist()}")
                print(f"Total NaNs per column:\n{nan_columns}")
    
                # Find UWIs with NaNs
                nan_rows = X[X.isna().any(axis=1)]
                print("\n🚨 UWIs with NaN values:")
                print(nan_rows.index.tolist())  # Print UWI indices that have NaNs
            else:
                print("✅ No NaNs detected in X.")

            # Check for NaNs in y (target variable)
            print("\n🔍 Checking for NaN values in y before training:")
            if y.isna().sum() > 0:
                print(f"⚠️ NaNs detected in target variable '{target_variable}'")
                print("\n🚨 UWIs with NaN target values:")
                print(y[y.isna()].index.tolist())  # Print UWIs with NaN target values
            else:
                print("✅ No NaNs detected in y.")

            # Initialize models
            models = {
                'Linear Regression': LinearRegression(),
                'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
                'Gradient Boosting': GradientBoostingRegressor(random_state=42)
            }

            # Initialize results storage
            results = {
                'Model': [],
                'R2 Score': [],
                'MAE': [],
                'RMSE': [],
                'Feature Importance': []
            }

            # Prepare K-fold cross validation
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            scaler = StandardScaler()

            # Run analysis for each model
            for model_name, model in models.items():
                r2_scores = []
                mae_scores = []
                rmse_scores = []
                feature_importance = np.zeros(X.shape[1])

                for train_idx, test_idx in kf.split(X):
                    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

                    # Scale the features
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)

                    # Train model
                    model.fit(X_train_scaled, y_train)

                    # Make predictions
                    y_pred = model.predict(X_test_scaled)

                    # Calculate metrics
                    r2_scores.append(r2_score(y_test, y_pred))
                    mae_scores.append(mean_absolute_error(y_test, y_pred))
                    rmse_scores.append(np.sqrt(mean_squared_error(y_test, y_pred)))

                    # Get feature importance
                    if model_name == 'Linear Regression':
                        feature_importance += np.abs(model.coef_)
                    else:
                        feature_importance += model.feature_importances_

                # Average the scores and feature importance
                feature_importance /= kf.n_splits
            
                # Store results
                results['Model'].append(model_name)
                results['R2 Score'].append(np.mean(r2_scores))
                results['MAE'].append(np.mean(mae_scores))
                results['RMSE'].append(np.mean(rmse_scores))
                results['Feature Importance'].append(dict(zip(X.columns, feature_importance)))

            # Show regression analysis dialog
            dialog = RegressionAnalysisDialog(
                results=results,
                target_variable=target_variable,
                parent=self
            )
            dialog.exec()

        except Exception as e:
            print("Error details:", str(e))
            print("Full traceback:", traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error running analysis: {str(e)}")

    # UWI selection helper methods remain the same
    def filter_UWIs(self, text):
        for i in range(self.available_UWIs.count()):
            item = self.available_UWIs.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def select_UWI(self):
        selected_items = self.available_UWIs.selectedItems()
        for item in selected_items:
            self.selected_UWIs.addItem(item.text())
            self.available_UWIs.takeItem(self.available_UWIs.row(item))

    def deselect_UWI(self):
        selected_items = self.selected_UWIs.selectedItems()
        for item in selected_items:
            self.available_UWIs.addItem(item.text())
            self.selected_UWIs.takeItem(self.selected_UWIs.row(item))

    def select_all_UWIs(self):
        for i in range(self.available_UWIs.count() - 1, -1, -1):
            item = self.available_UWIs.item(i)
            self.selected_UWIs.addItem(item.text())
            self.available_UWIs.takeItem(i)

    def deselect_all_UWIs(self):
        for i in range(self.selected_UWIs.count() - 1, -1, -1):
            item = self.selected_UWIs.item(i)
            self.available_UWIs.addItem(item.text())
            self.selected_UWIs.takeItem(i)


class RegressionAnalysisDialog(QDialog):
    def __init__(self, results, target_variable, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Regression Analysis Results - {target_variable}")
        self.setMinimumSize(1000, 800)
        
        layout = QVBoxLayout()
        
        # Create tabs for different visualizations
        tabs = QTabWidget()
        
        # Model Comparison Tab
        model_comparison_tab = QWidget()
        model_layout = QVBoxLayout()
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        
        # Plot model comparison
        model_names = results['Model']
        r2_scores = results['R2 Score']
        
        bars = ax1.bar(model_names, r2_scores)
        ax1.set_ylabel('R2 Score')
        ax1.set_title('Model Performance Comparison')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        canvas1 = FigureCanvasQTAgg(fig1)
        model_layout.addWidget(canvas1)
        model_comparison_tab.setLayout(model_layout)
        tabs.addTab(model_comparison_tab, "Model Comparison")
        
        # Feature Importance Tab
        feature_importance_tab = QWidget()
        feature_layout = QVBoxLayout()
        
        # Get feature importance from best model (highest R2)
        best_model_idx = np.argmax(results['R2 Score'])
        best_model_importance = results['Feature Importance'][best_model_idx]
        
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        
        # Sort feature importance
        sorted_importance = dict(sorted(best_model_importance.items(), 
                                      key=lambda x: abs(x[1]), 
                                      reverse=True))
        
        features = list(sorted_importance.keys())
        importance = list(sorted_importance.values())
        
        bars = ax2.barh(range(len(features)), importance)
        ax2.set_yticks(range(len(features)))
        ax2.set_yticklabels(features)
        ax2.set_xlabel('Feature Importance')
        ax2.set_title(f'Feature Importance ({results["Model"][best_model_idx]})')
        
        plt.tight_layout()
        
        canvas2 = FigureCanvasQTAgg(fig2)
        feature_layout.addWidget(canvas2)
        feature_importance_tab.setLayout(feature_layout)
        tabs.addTab(feature_importance_tab, "Feature Importance")
        
        layout.addWidget(tabs)
        
        # Add results table
        table = QTableWidget()
        table.setRowCount(len(results['Model']))
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Model', 'R2 Score', 'MAE', 'RMSE'])
        
        for i in range(len(results['Model'])):
            table.setItem(i, 0, QTableWidgetItem(results['Model'][i]))
            table.setItem(i, 1, QTableWidgetItem(f"{results['R2 Score'][i]:.3f}"))
            table.setItem(i, 2, QTableWidgetItem(f"{results['MAE'][i]:.3f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{results['RMSE'][i]:.3f}"))
        
        layout.addWidget(table)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)

# Example usage and testing:
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    
    class MockDBManager:
        def connect(self):
            pass
            
        def disconnect(self):
            pass
            
        def get_UWIs(self):
            return ['UWI1', 'UWI2', 'UWI3', 'UWI4', 'UWI5']
            
        def fetch_zone_names_by_type(self, zone_type):
            return [('Zone1',), ('Zone2',)]
            
        def fetch_zone_table_data(self, zone_name):
            # Mock data
            data = [
                ['UWI1', 100.0, 200.0, 300.0],
                ['UWI2', 150.0, 250.0, 350.0],
                ['UWI3', 175.0, 225.0, 375.0],
                ['UWI4', 125.0, 275.0, 325.0],
                ['UWI5', 160.0, 240.0, 360.0]
            ]
            columns = ['UWI', 'Value1', 'Value2', 'Value3']
            return data, columns

    app = QApplication(sys.argv)
    db_manager = MockDBManager()
    dialog = AttributeAnalyzer(db_manager)
    dialog.show()
    sys.exit(app.exec())