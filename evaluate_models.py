import pandas as pd
import joblib
import os
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

print("--- EVALUATING CLASSIFICATION MODEL (rf_model.pkl) ---")
try:
    df1 = pd.read_csv("food_impact_data_nofood.csv")
    X1 = df1.drop("impact", axis=1)
    y1 = df1["impact"]
    X_train1, X_test1, y_train1, y_test1 = train_test_split(X1, y1, test_size=0.2, random_state=42)
    
    model1 = joblib.load("rf_model.pkl")
    y_pred1 = model1.predict(X_test1)
    
    print(f"Accuracy: {accuracy_score(y_test1, y_pred1):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test1, y_pred1))
    
    importances1 = model1.feature_importances_
    features1 = X1.columns
    print("\nFeature Importances:")
    for f, imp in sorted(zip(features1, importances1), key=lambda x: x[1], reverse=True):
        print(f"  - {f}: {imp:.4f}")
except Exception as e:
    print(f"Error evaluating rf_model.pkl: {e}")

print("\n\n--- EVALUATING REGRESSION MODEL (body_impact_rf_v2.pkl) ---")
try:
    df2 = pd.read_csv("food_recommend_engine/body_impact_training_data.csv")
    df2 = df2.dropna()
    X2 = df2[['ba_ratio', 'heart_rate', 'hrv', 'temperature', 'sleep_hours', 'hydration_level', 'heat_factor']]
    y2 = df2['impact_score']
    
    X_train2, X_test2, y_train2, y_test2 = train_test_split(X2, y2, test_size=0.2, random_state=42)
    
    model2 = joblib.load("food_recommend_engine/body_impact_rf_v2.pkl")
    y_pred2 = model2.predict(X_test2)
    
    mse = mean_squared_error(y_test2, y_pred2)
    r2 = r2_score(y_test2, y_pred2)
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"R-squared (R2 Score): {r2:.4f}")
    
    importances2 = model2.feature_importances_
    features2 = X2.columns
    print("\nFeature Importances:")
    for f, imp in sorted(zip(features2, importances2), key=lambda x: x[1], reverse=True):
        print(f"  - {f}: {imp:.4f}")
except Exception as e:
    print(f"Error evaluating body_impact_rf_v2.pkl: {e}")
