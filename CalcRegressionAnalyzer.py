from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QSplitter,
                               QWidget, QLineEdit, QAbstractItemView, QMessageBox, 
                               QComboBox, QGroupBox, QCheckBox, QHeaderView, 
                               QGridLayout, QPushButton, QSizePolicy,QFileDialog)

from PySide6.QtCore import Qt

from PySide6.QtGui import QPalette, QColor
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

# Import styled widgets
from StyledDropdown import StyledDropdown
from StyledDropdown import StyledInputBox
from StyledTwoListSelector import TwoListSelector
from StyledButton import StyledButton



class CalcRegressionAnalyzer(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Well Regression Analysis")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
                # Calculate label widths for consistency
        labels = [
            "Regression",
            "Target Variable",
            "Description"
        ]


        labels_width = StyledDropdown.calculate_label_width(labels)
        print(labels_width)# Get fixed width


        # Main layout
        main_layout = QVBoxLayout(self)

        # Regression Selection Group
        regression_group = QGroupBox("Regression Selection")
        regression_layout = QVBoxLayout()


        # Styled Dropdown for Regression Selection
        self.regression_dropdown = StyledDropdown("Regression", editable=False)
        self.regression_dropdown.combo.currentIndexChanged.connect(self.regression_changed)
        regression_layout.addWidget(self.regression_dropdown)

        # Styled Dropdown for Target Variable
        self.target_dropdown = StyledDropdown("Target Variable", editable=False)
        regression_layout.addWidget(self.target_dropdown)

  
        # Styled Input Box (Now aligned with dropdowns)
        
        self.regression_description = StyledInputBox("Description", default_value="")  
        self.regression_description.label.setFixedWidth(labels_width) 
        self.regression_description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  
        regression_layout.addWidget(self.regression_description)



        regression_group.setLayout(regression_layout)
        main_layout.addWidget(regression_group)

        # UWI Selection using TwoListSelector
        uwi_group = QGroupBox("Well Selection")
        uwi_layout = QVBoxLayout()
        
        self.uwi_selector = TwoListSelector(
            left_title="Available UWIs", 
            right_title="Selected UWIs"
        )
        uwi_layout.addWidget(self.uwi_selector)
        uwi_group.setLayout(uwi_layout)
        main_layout.addWidget(uwi_group)

        # Button layout at the bottom right
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right
        
        # Close Button (Red)
        close_button = StyledButton("Close", "close")
        close_button.setFixedSize(100, 30)  # Standard button size
        close_button.clicked.connect(self.close)
        
        # Run Analysis Button (Green)
        btn_run = StyledButton("Run Analysis", "function")
        btn_run.setFixedSize(120, 30)  # Slightly wider to accommodate text
        btn_run.clicked.connect(self.run_analysis)
        
        # Add buttons to layout
        button_layout.addWidget(btn_run)
        button_layout.addWidget(close_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
        
        # Load initial data
        self.load_data()

    def regression_changed(self, index):
        """Handle regression selection change"""
        try:
            # Update description
            description = self.regression_dropdown.combo.itemData(index)
            self.regression_description.setText(description if description else "No description available")
            
            # Update target variables
            selected_regression = self.regression_dropdown.currentText()
            if selected_regression:
                attributes = self.db_manager.get_regression_attributes(selected_regression)
                
                self.target_dropdown.clear()
                if attributes:
                    # Extract just the attribute names from the tuples
                    attribute_names = [attr[0] for attr in attributes]
                    self.target_dropdown.setItems(attribute_names)
        except Exception as e:
            print(f"Error in regression_changed: {e}")
            QMessageBox.warning(self, "Error", f"Could not update regression details: {e}")
    def update_regression_description(self, index):
        """Update the description text when a regression is selected"""
        description = self.regression_combo.itemData(index)
        self.regression_description.setText(description if description else "No description available")

    def update_target_variables(self, index):
        """Update target variables dropdown when regression table is selected"""
        selected_regression = self.regression_combo.currentText()
        print(f"Updating target variables for: {selected_regression}")
    
        if selected_regression:
            attributes = self.db_manager.get_regression_attributes(selected_regression)
            print(f"Found target variables: {attributes}")
        
            self.target_combo.clear()
            if attributes:
                # Extract just the attribute names from the tuples
                attribute_names = [attr[0] for attr in attributes]
                self.target_combo.addItems(attribute_names)


    def load_data(self):
        """Load available UWIs and regression tables from the database"""
        try:
            # Load UWIs
            UWIs = self.db_manager.get_UWIs()
            self.uwi_selector.set_left_items(UWIs)
        
            # Load regression tables
            regression_tables = self.db_manager.get_regression_tables()
            
            # Clear existing items
            self.regression_dropdown.clear()
            
            # Populate regression dropdown
            for regression in regression_tables:
                regression_id, regression_name, values_table, attrs_table, description, date_created = regression
                self.regression_dropdown.combo.addItem(regression_name, description)  
        
            # Update description and target variables for first item
            if regression_tables:
                self.regression_changed(0)
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")

    def run_analysis(self):
        """Run multiple regression analyses and compare their performance."""
        try:
            # Get selected UWIs
            UWIs = self.uwi_selector.get_right_items()
            
            if not UWIs:
                QMessageBox.warning(self, "Invalid Selection", "Please select at least one UWI")
                return

            # Get selected regression table and target variable
            selected_regression = self.regression_dropdown.currentText()
            target_variable = self.target_dropdown.currentText()
            
            if not selected_regression or not target_variable:
                QMessageBox.warning(self, "Invalid Selection", "Please select both regression table and target variable")
                return

            # Fetch regression data
            regression_data = self.db_manager.get_regression_data(selected_regression, UWIs)
        
            if regression_data is None or regression_data.empty:
                QMessageBox.warning(self, "No Data", "No data found for the selected regression and UWIs")
                return

            # Pivot the data
            data_pivoted = regression_data.pivot_table(
                index='UWI',
                columns='attribute_name',
                values='attribute_value',
                aggfunc='first'
            ).reset_index()

            # Validate target variable exists
            if target_variable not in data_pivoted.columns:
                QMessageBox.warning(self, "Invalid Selection", 
                                    f"Target variable '{target_variable}' not found in data.")
                return

            # Separate features and target
            X = data_pivoted.drop([target_variable, 'UWI'], axis=1)
            y = data_pivoted[target_variable]

            # Perform preliminary data cleaning
            X_filtered = X.dropna()
            y_filtered = y[X_filtered.index]

            # Check for sufficient samples
            if len(X_filtered) < 5:
                QMessageBox.warning(self, "Insufficient Data", 
                                    f"Not enough samples for cross-validation. Found {len(X_filtered)} samples.")
                return

            # Initialize models
            models = {
                'Linear Regression': LinearRegression(),
                'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
                'Gradient Boosting': GradientBoostingRegressor(random_state=42)
            }

            # Perform cross-validation and collect results
            results = {
                'Model': [],
                'R2 Score': [],
                'MAE': [],
                'RMSE': [],
                'Feature Importance': []
            }

            # Scaling features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_filtered)

            # Perform cross-validation
            kf = KFold(n_splits=min(5, len(X_filtered)), shuffle=True, random_state=42)
            
            for model_name, model in models.items():
                r2_scores, mae_scores, rmse_scores = [], [], []
                feature_importance = np.zeros(X_filtered.shape[1])

                for train_idx, test_idx in kf.split(X_scaled):
                    X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
                    y_train, y_test = y_filtered.iloc[train_idx], y_filtered.iloc[test_idx]

                    # Train and predict
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)

                    # Calculate metrics
                    r2_scores.append(r2_score(y_test, y_pred))
                    mae_scores.append(mean_absolute_error(y_test, y_pred))
                    rmse_scores.append(np.sqrt(mean_squared_error(y_test, y_pred)))

                    # Get feature importance
                    if model_name == 'Linear Regression':
                        importance = np.abs(model.coef_)
                    else:
                        importance = model.feature_importances_
                    feature_importance += importance

                # Average metrics and feature importance
                feature_importance /= len(list(kf.split(X_scaled)))
                
                # Store results
                results['Model'].append(model_name)
                results['R2 Score'].append(np.mean(r2_scores))
                results['MAE'].append(np.mean(mae_scores))
                results['RMSE'].append(np.mean(rmse_scores))
                results['Feature Importance'].append(
                    dict(zip(X_filtered.columns, feature_importance))
                )
                
            # Show results (you'll need to implement RegressionAnalysisDialog)
            dialog = RegressionAnalysisDialog(
                results=results,
                target_variable=target_variable,
                db_manager=self.db_manager,
                regression_name=selected_regression,
                parent=self
            )
            dialog.exec()

        except Exception as e:
            print("Error details:", str(e))
            print("Full traceback:", traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error running analysis: {str(e)}")


class RegressionAnalysisDialog(QDialog):
    def __init__(self, results, target_variable, db_manager, regression_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Regression Analysis Results - {target_variable}")
        self.setMinimumSize(1200, 800)
        self.results = results
        self.db_manager = db_manager
        self.regression_name = regression_name
        self.target_variable = target_variable

        # Set black background
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)

        # Main layout as grid
        main_layout = QGridLayout()
        main_layout.setSpacing(20)

        # Metric selector directly above model performance section
        metric_layout = QHBoxLayout()
        metric_layout.addWidget(QLabel("Select Metric:"))
        self.metric_selector = QComboBox()
        self.metric_selector.addItems(['R2 Score', 'MAE', 'RMSE'])
        self.metric_selector.currentIndexChanged.connect(self.update_model_comparison)
        self.metric_selector.setMinimumWidth(150)
        metric_layout.addWidget(self.metric_selector)
        metric_layout.addStretch()
        main_layout.addLayout(metric_layout, 0, 0)  # Top left

        # Model selector directly above feature importance section
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Model:"))
        self.model_selector = QComboBox()
        self.model_selector.addItems(results['Model'])
        self.model_selector.currentIndexChanged.connect(self.update_feature_importance_table)
        self.model_selector.setMinimumWidth(150)
        selector_layout.addWidget(self.model_selector)
        selector_layout.addStretch()
        main_layout.addLayout(selector_layout, 2, 0)  # Above bottom left

        # Create fixed-size policy for plots
        fixed_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Model performance plot
        plot_container1 = QWidget()
        plot_layout1 = QVBoxLayout(plot_container1)
        plot_layout1.setContentsMargins(0, 0, 0, 0)  # Remove padding
        self.fig1, self.ax1 = plt.subplots(figsize=(8, 4))
        self.fig1.patch.set_facecolor('black')
        self.ax1.set_facecolor("black")
        self.canvas1 = FigureCanvasQTAgg(self.fig1)
        plot_layout1.addWidget(self.canvas1)
        plot_container1.setSizePolicy(fixed_size_policy)
        plot_container1.setFixedHeight(300)
        main_layout.addWidget(plot_container1, 1, 1)  # Right top

        # Model performance table
        self.model_table = QTableWidget()
        self.model_table.setRowCount(len(results['Model']))
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(['Model', 'R2 Score', 'MAE', 'RMSE'])
        self.model_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_table.setFixedHeight(300)
        self.model_table.horizontalHeader().setStretchLastSection(True)
        self.model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Style the table
        table_style = """
            QTableWidget {
                background-color: black;
                color: white;
                gridline-color: #404040;
                border: none;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
                padding: 5px;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: #1a1a1a;
            }
            QTableCornerButton::section {
                background-color: #2a2a2a;
                border: 1px solid #404040;
            }
            QScrollBar:vertical {
                background: black;
            }
            QScrollBar:horizontal {
                background: black;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #2a2a2a;
            }
            QHeaderView {
                background-color: black;
            }
        """
        self.model_table.setStyleSheet(table_style)

        # Populate model performance table
        for i in range(len(results['Model'])):
            # Only create table items if we have data
            if i < len(results['Model']):
                self.model_table.setItem(i, 0, QTableWidgetItem(results['Model'][i]))
                self.model_table.setItem(i, 1, QTableWidgetItem(f"{results['R2 Score'][i]:.3f}"))
                self.model_table.setItem(i, 2, QTableWidgetItem(f"{results['MAE'][i]:.3f}"))
                self.model_table.setItem(i, 3, QTableWidgetItem(f"{results['RMSE'][i]:.3f}"))
                
                # Right-align numeric columns
                for j in range(1, 4):
                    item = self.model_table.item(i, j)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Adjust row count to match actual data
        self.model_table.setRowCount(len(results['Model']))

        main_layout.addWidget(self.model_table, 1, 0)  # Left top

        # Feature importance plot
        plot_container2 = QWidget()
        plot_layout2 = QVBoxLayout(plot_container2)
        plot_layout2.setContentsMargins(0, 0, 0, 0)  # Remove padding
        self.fig2, self.ax2 = plt.subplots(figsize=(8, 4))
        self.fig2.patch.set_facecolor('black')
        self.ax2.set_facecolor("black")
        self.canvas2 = FigureCanvasQTAgg(self.fig2)
        plot_layout2.addWidget(self.canvas2)
        plot_container2.setSizePolicy(fixed_size_policy)
        plot_container2.setFixedHeight(300)
        main_layout.addWidget(plot_container2, 3, 1)  # Bottom right

        # Feature importance table
        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(2)
        self.feature_table.setHorizontalHeaderLabels(['Feature', 'Importance'])
        self.feature_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.feature_table.setFixedHeight(300)
        self.feature_table.horizontalHeader().setStretchLastSection(True)
        self.feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.feature_table.setStyleSheet(table_style)
        main_layout.addWidget(self.feature_table, 3, 0)  # Bottom left

        # Close button at the bottom
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch()  # Push buttons to the right

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
                padding: 5px 15px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)

        save_to_excel_button = QPushButton("Export to Excel")
        save_to_excel_button.clicked.connect(self.save_to_excel)
        save_to_excel_button.setStyleSheet(close_button.styleSheet())

        save_weights_button = QPushButton("Save Weights")
        save_weights_button.clicked.connect(self.save_model_weights)
        save_weights_button.setStyleSheet(close_button.styleSheet())

        bottom_button_layout.addWidget(save_to_excel_button)
        bottom_button_layout.addWidget(save_weights_button)
        bottom_button_layout.addWidget(close_button)

        # Replace the previous close button layout with this new layout
        main_layout.addLayout(bottom_button_layout, 4, 0, 1, 2)

        # Style for labels and combo boxes
        self.setStyleSheet("""
            QDialog, QLabel {
                color: white;
            }
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
                padding: 5px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-width: 0px;
            }
            QComboBox:hover {
                background-color: #404040;
            }
        """)

        self.setLayout(main_layout)

        # Initial updates
        self.update_model_comparison(0)
        self.update_feature_importance_table(0)

    def update_model_comparison(self, metric_idx):
        """Update model comparison plot with a horizontal bar chart"""
        self.ax1.clear()
        self.ax1.set_facecolor("black")
        
        # Set all spines and ticks to white
        for spine in self.ax1.spines.values():
            spine.set_color('white')
        self.ax1.tick_params(axis='both', colors='white')

        model_names = self.results['Model']
        metric_name = self.metric_selector.currentText()
        metric_values = self.results[metric_name]

        # Create horizontal bars with a color gradient
        colors = plt.cm.viridis(np.linspace(0, 1, len(model_names)))
        bars = self.ax1.barh(model_names, metric_values, color=colors)

        self.ax1.set_xlabel(metric_name, color='white', fontsize=10)
        self.ax1.set_title('Model Performance Comparison', color='white', fontsize=12, pad=20)

        # Add value labels with better positioning
        for bar, value in zip(bars, metric_values):
            x_pos = value + (max(metric_values) * 0.02)  # Offset for better readability
            self.ax1.text(x_pos, bar.get_y() + bar.get_height()/2.,
                         f'{value:.3f}', ha='left', va='center', color='white',
                         fontsize=9)

        # Adjust layout to prevent text cutoff
        self.fig1.tight_layout()
        self.canvas1.draw()

    def normalize_importance_to_weights(self, importance_dict):
        """Convert feature importances to weights that sum to 1.0"""
        # Get absolute values
        abs_values = {k: abs(v) for k, v in importance_dict.items()}
        total = sum(abs_values.values())
        
        # Normalize to sum to 1.0
        if total > 0:  # Avoid division by zero
            weights = {k: v/total for k, v in abs_values.items()}
        else:
            weights = importance_dict
            
        return weights

    def update_feature_importance_table(self, model_idx):
        """Update feature importance table for selected model"""
        if model_idx < len(self.results['Feature Importance']):
            model_importance = self.results['Feature Importance'][model_idx]
            
            # Convert to weights
            weights = self.normalize_importance_to_weights(model_importance)
            
            # Sort by weight value
            sorted_weights = dict(sorted(weights.items(),
                                       key=lambda x: x[1],
                                       reverse=True))

            # Set row count to match actual data
            self.feature_table.setRowCount(len(sorted_weights))
            
            # Update column headers to reflect weights
            self.feature_table.setHorizontalHeaderLabels(['Feature', 'Weight'])

            for i, (feature, weight) in enumerate(sorted_weights.items()):
                feature_item = QTableWidgetItem(feature)
                # Display as percentage
                weight_item = QTableWidgetItem(f"{weight:.1%}")
                
                # Right-align weight values
                weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                self.feature_table.setItem(i, 0, feature_item)
                self.feature_table.setItem(i, 1, weight_item)
            
            # Update the plot with weights
            self.update_feature_importance(model_idx, use_weights=True)
        else:
            # Clear the table if no data
            self.feature_table.setRowCount(0)

        # Auto-adjust column widths
        self.feature_table.resizeColumnsToContents()
        
        # Update feature importance plot
        self.update_feature_importance(model_idx)

    def update_feature_importance(self, model_idx, use_weights=True):
        """Update feature importance plot for selected model"""
        self.ax2.clear()
        self.ax2.set_facecolor("black")
        
        # Set all spines and ticks to white
        for spine in self.ax2.spines.values():
            spine.set_color('white')
        self.ax2.tick_params(axis='both', colors='white')

        model_importance = self.results['Feature Importance'][model_idx]
        model_name = self.results['Model'][model_idx]

        if use_weights:
            # Convert to weights
            values = self.normalize_importance_to_weights(model_importance)
            title_suffix = "Weights"
            xlabel = "Feature Weight (%)"
        else:
            values = model_importance
            title_suffix = "Importance"
            xlabel = "Feature Importance"

        # Sort by value
        sorted_values = dict(sorted(values.items(),
                                  key=lambda x: x[1],
                                  reverse=True))

        features = list(sorted_values.keys())
        if use_weights:
            importance_values = [v * 100 for v in sorted_values.values()]  # Convert to percentages
        else:
            importance_values = list(sorted_values.values())

        # Create horizontal bars with a color gradient
        colors = plt.cm.viridis(np.linspace(0, 1, len(features)))
        bars = self.ax2.barh(range(len(features)), importance_values, color=colors)

        self.ax2.set_yticks(range(len(features)))
        self.ax2.set_yticklabels(features, color='white')
        self.ax2.set_xlabel(xlabel, color='white', fontsize=10)
        self.ax2.set_title(f'Feature {title_suffix} ({model_name})', color='white', fontsize=12, pad=20)

        # Add value labels with better positioning
        for bar, value in zip(bars, importance_values):
            if use_weights:
                label = f"{value:.1f}%"
            else:
                label = f"{value:.3f}"
                
            x_pos = value + (max(importance_values) * 0.02)
            self.ax2.text(x_pos, bar.get_y() + bar.get_height()/2.,
                         label, ha='left', va='center', color='white',
                         fontsize=9)

        # Adjust layout to prevent text cutoff
        self.fig2.tight_layout()
        self.canvas2.draw()

    def save_to_excel(self):
        """Export model performance and feature importance tables to Excel"""
        try:
            # Open file dialog to choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Excel File", 
                f"{self.regression_name}_regression_analysis.xlsx", 
                "Excel Files (*.xlsx)"
            )

            if not file_path:
                return  # User canceled

            # Create a Pandas Excel writer using XlsxWriter as the engine
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Model Performance Sheet
                model_performance_df = pd.DataFrame({
                    'Model': self.results['Model'],
                    'R2 Score': self.results['R2 Score'],
                    'MAE': self.results['MAE'],
                    'RMSE': self.results['RMSE']
                })
                model_performance_df.to_excel(writer, sheet_name='Model Performance', index=False)

                # Feature Importance Sheet
                for i, model_name in enumerate(self.results['Model']):
                    feature_df = pd.DataFrame.from_dict(
                        self.results['Feature Importance'][i], 
                        orient='index', 
                        columns=['Importance']
                    ).reset_index()
                    feature_df.columns = ['Feature', 'Importance']
                    feature_df = feature_df.sort_values('Importance', ascending=False)
                    feature_df.to_excel(writer, sheet_name=f'{model_name} Feature Importance', index=False)

            # Show success message
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Analysis results exported to {file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to Excel: {str(e)}"
            )
            print(f"Excel export error: {traceback.format_exc()}")

    def save_model_weights(self):
        """Open dialog to edit and save feature weights"""
        try:
            # Get the selected model and its feature weights
            model_idx = self.model_selector.currentIndex()
            model_name = self.results['Model'][model_idx]
            feature_weights = self.results['Feature Importance'][model_idx]

            # Normalize weights to sum to 1.0
            total_weight = sum(abs(v) for v in feature_weights.values())
            normalized_weights = {k: abs(v)/total_weight for k, v in feature_weights.items()}

            # Open weights edit dialog
            weights_dialog = ModelWeightsEditDialog(
                model_name=model_name, 
                feature_weights=normalized_weights, 
                parent=self
            )
        
            # If dialog is accepted, save the weights
            if weights_dialog.exec() == QDialog.Accepted:
                # Get the adjusted weights from the dialog
                adjusted_weights = weights_dialog.adjusted_weights

                self.db_manager.save_regression_feature_weights(
                    self.regression_name, 
                    adjusted_weights,
                    self.target_variable  # Pass the target variable
                )


                # Show success message
                QMessageBox.information(
                    self, 
                    "Weights Saved", 
                    f"Feature weights for {model_name} model saved successfully."
                )

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Save Weights Error", 
                f"Failed to save weights: {str(e)}"
            )
            print(f"Save weights error: {traceback.format_exc()}")



class ModelWeightsEditDialog(QDialog):
    def __init__(self, model_name, feature_weights, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{model_name} Feature Weights")
        self.setMinimumSize(600, 400)
        self.original_weights = feature_weights

        # Normalize weights before displaying
        max_weight = max(feature_weights.values())
        normalized_weights = {k: (v / max_weight * 100) for k, v in feature_weights.items()}

        # Main layout
        main_layout = QVBoxLayout()

        # Weights table
        self.weights_table = QTableWidget()
        self.weights_table.setColumnCount(4)
        self.weights_table.setHorizontalHeaderLabels(['Feature', 'Original Weight', 'Normalized Weight', 'Adjusted Weight'])
        
        # Table styling
        table_style = """
            QTableWidget {
                background-color: black;
                color: white;
                gridline-color: #404040;
                border: none;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
                padding: 5px;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: black;
            }
            QTableWidget::item:disabled {
                background-color: black;
            }
            QTableCornerButton::section {
                background-color: black;
                border: none;
            }
        """
        self.weights_table.setStyleSheet(table_style)
        
        # Populate table
        sorted_weights = dict(sorted(feature_weights.items(), 
                                     key=lambda x: x[1], 
                                     reverse=True))
        
        self.weights_table.setRowCount(len(sorted_weights))
        
        for row, (feature, weight) in enumerate(sorted_weights.items()):
            # Feature name
            feature_item = QTableWidgetItem(feature)
            feature_item.setFlags(feature_item.flags() & ~Qt.ItemIsEditable)
            feature_item.setBackground(QColor(0, 0, 0))
            self.weights_table.setItem(row, 0, feature_item)
            
            # Original weight (read-only)
            original_weight_item = QTableWidgetItem(f"{weight:.1f}")
            original_weight_item.setFlags(original_weight_item.flags() & ~Qt.ItemIsEditable)
            original_weight_item.setForeground(QColor(150, 150, 150))
            original_weight_item.setBackground(QColor(0, 0, 0))
            self.weights_table.setItem(row, 1, original_weight_item)
            
            # Normalized weight (read-only)
            normalized_weight = normalized_weights[feature]
            normalized_item = QTableWidgetItem(f"{normalized_weight:.1f}")
            normalized_item.setFlags(normalized_item.flags() & ~Qt.ItemIsEditable)
            normalized_item.setForeground(QColor(200, 200, 200))
            normalized_item.setBackground(QColor(0, 0, 0))
            self.weights_table.setItem(row, 2, normalized_item)
            
            # Editable weight
            weight_item = QTableWidgetItem(f"{normalized_weight:.1f}")
            weight_item.setBackground(QColor(0, 0, 0))
            self.weights_table.setItem(row, 3, weight_item)
        
        # Resize columns and rows
        self.weights_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.weights_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.weights_table.verticalHeader().setVisible(False)
        self.weights_table.resizeColumnsToContents()
        self.weights_table.resizeRowsToContents()
        self.weights_table.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        main_layout.addWidget(self.weights_table)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Save button
        save_button = QPushButton("Save Weights")
        save_button.clicked.connect(self.save_weights)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        button_layout.addWidget(save_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(save_button.styleSheet())
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: black;
                color: white;
            }
            QLabel, QCheckBox {
                color: white;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #404040;
            }
        """)

    def save_weights(self):
        """Validate and save weights"""
        try:
            # Collect new weights
            new_weights = {}
            for row in range(self.weights_table.rowCount()):
                feature = self.weights_table.item(row, 0).text()
                weight_str = self.weights_table.item(row, 3).text()
                
                # Validate weight
                try:
                    weight = float(weight_str)
                    if weight < 0 or weight > 100:
                        raise ValueError("Weights must be between 0 and 100")
                    new_weights[feature] = weight
                except ValueError:
                    QMessageBox.warning(
                        self, 
                        "Invalid Weight", 
                        f"Invalid weight for feature {feature}. Please enter a number between 0 and 100."
                    )
                    return
            
            # Scale weights so the largest becomes 100
            max_weight = max(new_weights.values())
            if max_weight > 0:
                scaled_weights = {k: (v / max_weight * 100) for k, v in new_weights.items()}
            else:
                scaled_weights = new_weights
            
            # Update the table with normalized weights
            for row in range(self.weights_table.rowCount()):
                feature = self.weights_table.item(row, 0).text()
                normalized_weight = scaled_weights[feature]
                self.weights_table.item(row, 3).setText(f"{normalized_weight:.1f}")
            
            # Return the scaled weights
            self.adjusted_weights = scaled_weights
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to save weights: {str(e)}"
            )
