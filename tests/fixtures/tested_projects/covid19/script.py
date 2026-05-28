import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import random
import math
import time
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import datetime
import operator 

data = pd.read_csv('data/covid19.csv')

# Cleaning the data
## Filling NaN entries
# data[['Province/State']] = data[['Province/State']].fillna('')

## Removing negative values in 'confirmed' and 'deaths' columns
# average_confirmed_count = data['Confirmed'].mean()
# data.loc[(data['Confirmed'] < 0), 'Confirmed'] = average_confirmed_count

# average_death_count = data['Deaths'].mean()
# data.loc[(data['Deaths'] < 0), 'Deaths'] = average_death_count

## Filling missing values with 0s
# data[['Confirmed', 'Deaths', 'Recovered']] = data[['Confirmed', 'Deaths', 'Recovered']].fillna(0)

# Save cleaned dataset as CSV file
# data.to_csv('data/covid19_clean.csv', index=False)

# Read the clean file
# data = pd.read_csv('data/covid19_clean.csv')
# data.fillna(data.mean(), inplace=True)

# Extract data
dates = pd.unique(data['Date'])
countries = pd.unique(data['Country/Region'])

world_cases = []
world_deaths = []
world_recovered = []

for date in dates:
    confirmed = data.loc[data['Date'] == date, 'Confirmed']
    deaths = data.loc[data['Date'] == date, 'Deaths']
    recovered = data.loc[data['Date'] == date, 'Recovered']
    total_confirmed = confirmed.sum()
    total_deaths = deaths.sum()
    total_recovered = recovered.sum()
    world_cases.append(total_confirmed)
    world_deaths.append(total_deaths)
    world_recovered.append(total_recovered)

# Total days since the beggining of the epidemic
epidemic_days = np.array([i for i in range(len(dates))]).reshape(-1, 1)
# Number of confirmed cases worldwide
world_cases = np.array(world_cases).reshape(-1, 1)
# Number of death counts worldwide
world_deaths = np.array(world_deaths).reshape(-1, 1)
# Number of recovered patients worldwide
world_recovered = np.array(world_recovered).reshape(-1, 1)

# Amount of days to be forecasted
day_span = 30
forecast = np.array([i for i in range(len(dates) + day_span)]).reshape(-1, 1)

start = start_date = datetime.datetime.strptime('1/22/2020', '%m/%d/%Y')
forecast_dates = []
for i in range(len(forecast)):
        forecast_dates.append((start_date + datetime.timedelta(days=i)).strftime('%m/%d/%Y'))

# Predict confirmed cases 
X_train_confirmed, X_test_confirmed, y_train_confirmed, y_test_confirmed = train_test_split(epidemic_days, world_cases, test_size=0.25, shuffle=False) 

svm_confirmed = SVR(shrinking=True, kernel='poly',gamma=0.01, epsilon=1, degree=5, C=0.1)
svm_confirmed.fit(X_train_confirmed, y_train_confirmed)
svm_pred = svm_confirmed.predict(forecast)

svm_test_pred = svm_confirmed.predict(X_test_confirmed)
plt.plot(y_test_confirmed)
plt.plot(svm_test_pred)
plt.legend(['Data', 'Forecast'])
print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))
print('MSE:',mean_squared_error(svm_test_pred, y_test_confirmed))

plt.show()

# Predict deaths
X_train_deaths, X_test_deaths, y_train_deaths, y_test_deaths = train_test_split(epidemic_days, world_deaths, test_size=0.25, shuffle=False) 

svm_deaths = SVR(shrinking=True, kernel='poly',gamma=0.01, epsilon=1,degree=5, C=0.1)
svm_deaths.fit(X_train_deaths, y_train_deaths)
svm_pred = svm_deaths.predict(forecast)

svm_test_pred = svm_deaths.predict(X_test_deaths)
plt.plot(y_test_deaths)
plt.plot(svm_test_pred)
plt.legend(['Data', 'Forecast'])
print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))
print('MSE:',mean_squared_error(svm_test_pred, y_test_confirmed))

plt.show()

# Predict recovered
X_train_recovered, X_test_recovered, y_train_recovered, y_test_recovered = train_test_split(epidemic_days, world_recovered, test_size=0.25, shuffle=False) 

svm_recovered = SVR(shrinking=True, kernel='poly',gamma=0.01, epsilon=1,degree=5, C=0.1)
svm_recovered.fit(X_train_recovered, y_train_recovered)
svm_pred = svm_recovered.predict(forecast)

svm_test_pred = svm_recovered.predict(X_test_recovered)
plt.plot(y_test_recovered)
plt.plot(svm_test_pred)
plt.legend(['Data', 'Forecast'])
print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))
print('MSE:',mean_squared_error(svm_test_pred, y_test_confirmed))

plt.show()

# Polinomial regression
poly = PolynomialFeatures(degree=3)
poly_X_train_confirmed = poly.fit_transform(X_train_confirmed)
poly_X_test_confirmed = poly.fit_transform(X_test_confirmed)
poly_future_forcast = poly.fit_transform(forecast)

bayesian_poly = PolynomialFeatures(degree=4)
bayesian_poly_X_train_confirmed = bayesian_poly.fit_transform(X_train_confirmed)
bayesian_poly_X_test_confirmed = bayesian_poly.fit_transform(X_test_confirmed)
bayesian_poly_future_forcast = bayesian_poly.fit_transform(forecast)

# polynomial regression
linear_model = LinearRegression(normalize=True, fit_intercept=False)
linear_model.fit(poly_X_train_confirmed, y_train_confirmed)
test_linear_pred = linear_model.predict(poly_X_test_confirmed)
linear_pred = linear_model.predict(poly_future_forcast)
print('MAE:', mean_absolute_error(test_linear_pred, y_test_confirmed))
print('MSE:',mean_squared_error(test_linear_pred, y_test_confirmed))

plt.plot(y_test_confirmed)
plt.plot(test_linear_pred)
plt.legend(['Test Data', 'Polynomial Regression Predictions'])
plt.show()
