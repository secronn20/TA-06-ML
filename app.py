
import os
import numpy as np
import pandas as pd

from flask import Flask, render_template, request, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "inventory-optimization-tp07"

# =====================================================
# PATH
# =====================================================

DATA_PATH = os.path.join(
    BASE_DIR, "data", "processed", "daily_demand.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR, "models", "q_table.npy"
)

TRAINING_PATH = os.path.join(
    BASE_DIR, "results", "training_history.csv"
)

# =====================================================
# CONFIGURATION
# =====================================================

CONFIG = {
    "initial_stock": 200,
    "max_capacity": 500,
    "order_fixed_cost": 5.0,
    "order_unit_cost": 0.50,
    "holding_cost": 0.05,
    "stockout_penalty": 2.0
}

ACTIONS = [0, 100, 200, 300]

ACTION_LABELS = [
    "Tidak Memesan",
    "Pesan 100 Unit",
    "Pesan 200 Unit",
    "Pesan 300 Unit"
]

# =====================================================
# LOAD DATA
# =====================================================

def load_data():

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError("Dataset tidak ditemukan.")

    df = pd.read_csv(DATA_PATH)

    # Menyesuaikan dengan format hasil preprocessing
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})

    if "Demand" not in df.columns:
        if "Quantity" in df.columns:
            df = df.rename(columns={"Quantity": "Demand"})
        else:
            raise ValueError("Kolom Demand tidak ditemukan.")

    df["Date"] = pd.to_datetime(df["Date"])
    df["Demand"] = pd.to_numeric(df["Demand"])

    if df.empty or df["Demand"].isna().any():
        raise ValueError("Dataset kosong atau tidak valid.")

    if (df["Demand"] < 0).any():
        raise ValueError("Demand tidak boleh negatif.")

    return df


def load_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Q-Table tidak ditemukan.")

    q_table = np.load(MODEL_PATH)

    if q_table.shape != (9, 4):
        raise ValueError("Ukuran Q-Table harus (9, 4).")

    if not np.isfinite(q_table).all():
        raise ValueError("Q-Table tidak valid.")

    return q_table


# =====================================================
# DEMAND CLASSIFICATION
# =====================================================

def classify_demand(demands):

    series = pd.Series(demands, dtype=float)

    signal = (
        series.shift(1)
        .rolling(7, min_periods=1)
        .mean()
        .fillna(0)
    )

    split = int(len(series) * 0.8)

    q33 = signal.iloc[:split].quantile(0.33)
    q66 = signal.iloc[:split].quantile(0.66)

    categories = np.where(
        signal <= q33, 0,
        np.where(signal <= q66, 1, 2)
    )

    return categories


# =====================================================
# INVENTORY ENVIRONMENT
# =====================================================

class InventoryEnvironment:

    def __init__(self, demands, categories, config):

        self.demands = np.array(demands, dtype=int)
        self.categories = np.array(categories, dtype=int)
        self.config = config

        self.reset()

    def reset(self):

        self.day = 0
        self.stock = self.config["initial_stock"]

        self.history = []

        return self.get_state()

    def get_state(self):

        if self.stock <= 100:
            inventory_state = 0
        elif self.stock <= 250:
            inventory_state = 1
        else:
            inventory_state = 2

        demand_state = int(self.categories[self.day])

        return inventory_state * 3 + demand_state

    def step(self, action):

        order = ACTIONS[action]

        actual_order = min(
            order,
            self.config["max_capacity"] - self.stock
        )

        order_cost = 0

        if actual_order > 0:
            order_cost = (
                self.config["order_fixed_cost"]
                + actual_order * self.config["order_unit_cost"]
            )

        available = self.stock + actual_order

        demand = int(self.demands[self.day])

        sold = min(available, demand)

        shortage = max(0, demand - available)

        ending_stock = available - sold

        holding_cost = (
            ending_stock * self.config["holding_cost"]
        )

        shortage_cost = (
            shortage * self.config["stockout_penalty"]
        )

        total_cost = (
            order_cost + holding_cost + shortage_cost
        )

        reward = -total_cost

        self.stock = ending_stock

        self.history.append({
            "day": self.day + 1,
            "demand": demand,
            "order": actual_order,
            "sold": sold,
            "ending_stock": ending_stock,
            "shortage": shortage,
            "total_cost": round(total_cost, 2),
            "reward": round(reward, 2)
        })

        self.day += 1

        done = self.day >= len(self.demands)

        next_state = None if done else self.get_state()

        return next_state, reward, done


# =====================================================
# SIMULATION
# =====================================================

def run_simulation(method="q_learning", initial_stock=200):

    df = load_data()

    q_table = load_model()

    demands = df["Demand"].values.astype(int)

    categories = classify_demand(demands)

    split = int(len(demands) * 0.8)

    test_demands = demands[split:]
    test_categories = categories[split:]

    config = CONFIG.copy()
    config["initial_stock"] = initial_stock

    env = InventoryEnvironment(
        test_demands,
        test_categories,
        config
    )

    state = env.reset()

    done = False

    while not done:

        if method == "q_learning":
            action = int(np.argmax(q_table[state]))

        elif method == "reorder_point":
            if env.stock <= 100:
                action = 3
            elif env.stock <= 200:
                action = 2
            else:
                action = 0

        else:
            action = 0

        state, reward, done = env.step(action)

    return pd.DataFrame(env.history)


# =====================================================
# METRICS
# =====================================================

def calculate_metrics(df):

    total_demand = df["demand"].sum()
    total_sold = df["sold"].sum()

    return {
        "total_demand": int(total_demand),
        "total_sold": int(total_sold),
        "total_order": int(df["order"].sum()),
        "total_shortage": int(df["shortage"].sum()),
        "total_cost": round(float(df["total_cost"].sum()), 2),
        "average_stock": round(float(df["ending_stock"].mean()), 2),
        "fill_rate": round(
            total_sold / total_demand * 100
            if total_demand else 0, 2
        )
    }


# =====================================================
# DASHBOARD
# =====================================================

@app.route("/")
def index():

    try:

        df = load_data()

        result = run_simulation("q_learning")

        metrics = calculate_metrics(result)

        return render_template(
            "index.html",
            product="JUMBO BAG RED RETROSPOT",
            metrics=metrics,
            dataset_days=len(df),
            chart_data=result.to_dict("records")
        )

    except Exception as e:

        return render_template(
            "index.html",
            error=str(e),
            product="JUMBO BAG RED RETROSPOT",
            metrics=None,
            dataset_days=0,
            chart_data=[]
        )


# =====================================================
# SIMULATION PAGE
# =====================================================

@app.route("/simulation", methods=["GET", "POST"])
def simulation():

    result = None
    metrics = None
    method = "q_learning"
    initial_stock = 200

    if request.method == "POST":

        try:

            method = request.form.get(
                "method", "q_learning"
            )

            initial_stock = int(
                request.form.get("initial_stock", 200)
            )

            if not 0 <= initial_stock <= 500:
                raise ValueError("Stok awal harus 0–500.")

            if method not in [
                "q_learning",
                "reorder_point",
                "no_order"
            ]:
                raise ValueError("Metode tidak valid.")

            result = run_simulation(
                method,
                initial_stock
            )

            metrics = calculate_metrics(result)

        except Exception as e:
            flash(str(e), "danger")

    return render_template(
        "simulation.html",
        result=result.to_dict("records") if result is not None else None,
        metrics=metrics,
        method=method,
        initial_stock=initial_stock
    )


# =====================================================
# EVALUATION PAGE
# =====================================================

@app.route("/evaluation")
def evaluation():

    methods = {
        "Q-Learning": "q_learning",
        "Reorder Point": "reorder_point",
        "Tanpa Pemesanan": "no_order"
    }

    comparison = {}

    for name, method in methods.items():

        result = run_simulation(method)

        comparison[name] = calculate_metrics(result)

    return render_template(
        "evaluation.html",
        comparison=comparison
    )


# =====================================================
# MODEL PAGE
# =====================================================

@app.route("/model")
def model():

    q_table = load_model()

    q_data = []

    for state in range(9):

        best_action = int(
            np.argmax(q_table[state])
        )

        q_data.append({
            "state": state,
            "inventory": [
                "Rendah", "Sedang", "Tinggi"
            ][state // 3],
            "demand": [
                "Rendah", "Sedang", "Tinggi"
            ][state % 3],
            "values": q_table[state].tolist(),
            "best_action": ACTION_LABELS[best_action]
        })

    training = []

    if os.path.exists(TRAINING_PATH):

        training_df = pd.read_csv(TRAINING_PATH)

        training = training_df.to_dict("records")

    return render_template(
        "model.html",
        q_data=q_data,
        training=training
    )


# =====================================================
# DOWNLOAD RESULT
# =====================================================

@app.route("/download")
def download():

    from flask import Response
    import csv
    import io

    result = run_simulation("q_learning")

    output = io.StringIO()

    result.to_csv(output, index=False)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=inventory_results.csv"
        }
    )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
