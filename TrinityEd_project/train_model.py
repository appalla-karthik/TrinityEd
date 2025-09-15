import os
import sys
import django
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TrinityEd_project.settings")  # Replace with your project name
django.setup()

# Dummy training data (replace with real data from Student model later)
X = np.array([[90, 85], [80, 75], [70, 65], [60, 55], [95, 90], [50, 45], [85, 80], [65, 60], [75, 70], [55, 50]])
y = np.array([0, 0, 1, 1, 0, 1, 0, 1, 0, 1])  # 1 = at-risk, 0 = not at-risk

# Split data for training/testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = LogisticRegression()
model.fit(X_train, y_train)

# Evaluate (optional)
y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred)}")

# Save the model (ensure ml_models/ directory exists or create it)
if not os.path.exists('ml_models'):
    os.makedirs('ml_models')
joblib.dump(model, 'ml_models/at_risk_model.pkl')
print("Model saved!")