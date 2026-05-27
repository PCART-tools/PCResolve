# standard and user-defined functions imports
import pandas as pd
import numpy as np
import wrangle
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import LinearRegression,LassoLars,TweedieRegressor
from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures

def lr_best_hyperparameter(X_train,y_train):
    '''This function will input X,y and variation in hyperparameters and
    outputs best hyperparameter'''
    #define hyperparamters
    params = {'normalize': [ True, False],
          'fit_intercept': [True, False]}
    #create grid object
    grid = GridSearchCV(LinearRegression(), params, cv=5)
    #fit grid object
    grid.fit(X_train,y_train.colonies_lost)
    #get best hyperparameters
    best = grid.best_estimator_
    
    #return output
    return best
    

def ll_best_hyperparameter(X_train,y_train):
    '''This function will input X,y and variation in hyperparameters and
    outputs best hyperparameter'''
    #define hyperparamters
    params = {
          'normalize': [True, False],
          'fit_intercept':[True, False],
           'alpha': [1,2,3,4]
         }
    #create grid object
    grid = GridSearchCV(LassoLars(), params, cv=5)
    #fit grid object
    grid.fit(X_train,y_train.colonies_lost)
    #get best hyperparameters
    best = grid.best_estimator_
    
    #return output
    return best



def tr_best_hyperparameter(X_train,y_train):
    '''This function will input X,y and variation in hyperparameters and
    outputs best hyperparameter'''
    #define hyperparameters
    params = {
          'power': [0, 1,2,3],
           'fit_intercept' : [True , False],
          'warm_start': [True, False], 
           'alpha': [1,2,3,4,5]
}
    #create grid object
    grid = GridSearchCV(TweedieRegressor(), params, cv=5,scoring = 'neg_root_mean_squared_error')
    #fit grid object
    grid.fit(X_train,y_train.colonies_lost)
    #get best parameters
    best = grid.best_estimator_
    
    #return output
    return best
    
