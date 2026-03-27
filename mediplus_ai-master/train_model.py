import kagglehub
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# 1. This line AUTOMATICALLY finds the correct path on YOUR computer
print("Locating dataset...")
KAGGE_DATA_PATH = kagglehub.dataset_download("kaushil268/disease-prediction-using-machine-learning")

# 2. Set the output directory for the AI models
MODEL_DIR = os.path.join('app', 'ai_models')
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

# 3. Read the data (Now it will find Training.csv correctly)
print(f"Reading clinical data from: {KAGGE_DATA_PATH}")
train_df = pd.read_csv(os.path.join(KAGGE_DATA_PATH, "Training.csv"))

# --- REST OF YOUR CODE ---
X = train_df.drop('prognosis', axis=1)
y = train_df['prognosis']

print("Training Random Forest Engine...")
model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)

joblib.dump(model, os.path.join(MODEL_DIR, 'disease_model.pkl'))
joblib.dump(X.columns.tolist(), os.path.join(MODEL_DIR, 'symptoms_list.pkl'))

print(f"✅ Success! 'Brain' saved to: {MODEL_DIR}")