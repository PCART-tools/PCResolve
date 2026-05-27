# Basic Data Science Imports
import pandas as pd
import numpy as np
import os
import wrangle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()

# Stats and M odeling imports
from scipy import stats
from math import sqrt
import regression_models as model
from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error,explained_variance_score, r2_score
from sklearn.linear_model import LinearRegression,LassoLars,TweedieRegressor
from sklearn.feature_selection import SelectKBest, RFE, f_regression
from sklearn.model_selection import train_test_split
import sklearn.preprocessing
from sklearn.metrics import mean_squared_error,explained_variance_score, r2_score
from sklearn.linear_model import LinearRegression,LassoLars,TweedieRegressor
from sklearn.feature_selection import SelectKBest, RFE, f_regression
from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures
from sklearn.model_selection import GridSearchCV




def split_data(df):
    '''This function takes in a dataframe and returns three dataframes, a training dataframe with 60 percent 
        of the data, a validate dataframe with 20 percent of the data and test dataframe with 20 percent of the data.'''
    # split data into train and test with a test size of 20 percent and random state of 825
    train, test = train_test_split(df, test_size=.2, random_state=825)
    # split train again into train and validate with a validate size of 25 percent of train
    train, validate = train_test_split(train, test_size=.25, random_state=825)
    # return three dataframes, 60/20/20 split
    return train, validate, test


# plot to visualize actual vs predicted. 
def model_performace(y_validate):
    """This function will take in y validate and output model perforamce visualization"""
    #set figure size
    plt.figure(figsize=(16,8))
    #histogram distribution of target
    plt.hist(y_validate.colonies_lost, color='blue', alpha=.5, label="Actual colony lost", bins = 1000)
    #histogram distribution of target predicted by linear regression model
    plt.hist(y_validate.colonies_lost_pred_lm, color='red', alpha=.5, label="Model: LinearRegression", bins = 1000)
    #histogram distribution of target predicted by Tweedie regressor model
    plt.hist(y_validate.colonies_lost_pred_glm, color='yellow', alpha=.5, label="Model: TweedieRegressor", bins = 1000)
    #histogram distribution of target predicted by LassoLars model
    plt.hist(y_validate.colonies_lost_pred_lars, color='green', alpha=.5, label="Model:Lassolars", bins = 1000)
    #histogram distribution of target predicted by Polynomial model
    plt.hist(y_validate.colonies_lost_pred_lm2, color="cyan", alpha=.5, label="Model 2nd degree Polynomial", bins = 1000)
    plt.xlabel("colony lost")
    plt.ylabel("count")
    plt.title("Comparing the distribution of actual colony lost to predicted distributions for the top models")
    plt.xlim(0,2500)
    plt.legend()
    plt.show()


def RMSE(X_train,y_train, X_validate, y_validate):
    '''
    this function will calculate baseline mean and baseline median and calculate RMSE from mean and median
    '''
    #get mean of target from train
    y_train["baseline_mean"] = y_train.colonies_lost.mean()
    #get median of target from train
    y_train["baseline_median"] =y_train.colonies_lost.median()
    #get mean of target from validate
    y_validate["baseline_mean"] = y_validate.colonies_lost.mean()
    #get median from target from validate
    y_validate["baseline_median"] =y_validate.colonies_lost.median()
    
    #calculate RMSE 
    RMSE_train_mean=mean_squared_error(y_train.colonies_lost,y_train.baseline_mean, squared = False)
    RMSE_validate_mean=mean_squared_error(y_validate.colonies_lost,y_validate.baseline_mean, squared = False)

    #print("RMSE using Mean on \nTrain: ", round(RMSE_train_mean,2), "\nValidate: ", round(RMSE_validate_mean,2))
    #print()

    #calculate RMSE
    RMSE_train_median= mean_squared_error(y_train.colonies_lost,y_train.baseline_median, squared = False)
    RMSE_validate_median= mean_squared_error(y_validate.colonies_lost,y_validate.baseline_median, squared = False)

    #print("RMSE using Median on \nTrain: ", round(RMSE_train_median,2), "\nValidate: ", round(RMSE_validate_median,2))
    
    #make a dataframe to capture model and RMSE 
    metric_df = pd.DataFrame(data=[
            {
                'model': 'Baseline', 
                'RMSE_train': RMSE_train_mean,
                'RMSE_validate': RMSE_validate_mean
                }
            ])
    
    
    # create the model object
    lm = LinearRegression(normalize = True)
    # Fit the model
    lm.fit(X_train, y_train.colonies_lost)
    # Predict y on train
    y_train['colonies_lost_pred_lm'] = lm.predict(X_train)
    # predict validate
    y_validate['colonies_lost_pred_lm'] = lm.predict(X_validate)
    
    # evaluate: train rmse
    rmse_train_lm= round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pred_lm,squared = False), 2)
    # evaluate: validate rmse
    rmse_validate_lm= round(mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lost_pred_lm,squared = False),2)

    #append model and RMSE from OLS model to metric dataframe
    metric_df = metric_df.append({
    'model': 'OLS Regressor(normalize = True)', 
    'RMSE_train': rmse_train_lm,
    'RMSE_validate': rmse_validate_lm,
    }, ignore_index=True)
    
    
    # create the model object
    lars = LassoLars(alpha=1, random_state = 825)
    # fit the model.
    lars.fit(X_train, y_train.colonies_lost)
    # predict train
    y_train['colonies_lost_pred_lars'] = lars.predict(X_train)
    # predict validate
    y_validate['colonies_lost_pred_lars'] = lars.predict(X_validate)
    # evaluate: train rmse
    rmse_train_lars = round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pred_lars, squared = False),2)
    # evaluate: validate rmse
    rmse_validate_lars= round(mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lost_pred_lars,squared = False),2)

    #append model and RMSE from LASSOLARS model to metric dataframe
    metric_df = metric_df.append({
    'model': 'LASSOLARS(alpha=1, normalize=True)', 
    'RMSE_train': rmse_train_lars,
    'RMSE_validate': rmse_validate_lars,
    }, ignore_index=True)
    
    
    
    # create the model object
    glm = TweedieRegressor(alpha=5, power=1, warm_start=True)
    # fit the model to our training data.
    glm.fit(X_train, y_train.colonies_lost)
    # predict train
    y_train['colonies_lost_pred_glm'] = glm.predict(X_train)
    # predict validate
    y_validate['colonies_lost_pred_glm'] = glm.predict(X_validate)
    # evaluate: train rmse
    rmse_train_tw = round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pred_glm,squared = False),2)
    # evaluate: validate rmse
    rmse_validate_tw= round(mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lost_pred_glm, squared = False),2)

    #append model and RMSE from GLM model to metric dataframe
    metric_df = metric_df.append({
    'model': 'Tweedie Regressor(alpha=5, power=1, warm_start=True)', 
    'RMSE_train': rmse_train_tw,
    'RMSE_validate': rmse_validate_tw,
    }, ignore_index=True)
    
    
    
    
    #create model object
    pf= PolynomialFeatures(degree= 2)
    # fit and transform X_train_scaled
    X_train_degree2 = pf.fit_transform(X_train)
    # transform X_validate_scaled 
    X_validate_degree2 = pf.transform(X_validate)

    # create the model object
    lm2 = LinearRegression(normalize=True)
    # fit the model to our training data. We must specify the column in y_train,  
    lm2.fit(X_train_degree2, y_train.colonies_lost)
    # predict train
    y_train['colonies_lost_pred_lm2'] = lm2.predict(X_train_degree2)
    # predict validate
    y_validate['colonies_lost_pred_lm2'] = lm2.predict(X_validate_degree2)

    # evaluate: train rmse
    rmse_train_py= round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pred_lm2, squared = False),2)
    # evaluate: validate rmse
    rmse_validate_py= round(mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lost_pred_lm2, squared = False) , 2)

    #append model and RMSE from Polynomial Regression model to metric dataframe
    metric_df = metric_df.append({
    'model': 'Polynomial Regression(degree = 2)', 
    'RMSE_train': rmse_train_py,
    'RMSE_validate': rmse_validate_py,
    }, ignore_index=True)
    
    
    return(pd.DataFrame(metric_df))


# create the model object
def test_rmse(X_train,y_train,X_test,y_test):
    """This function will input train and test data and output RMSE scores on test and baseline"""
    #create object
    lars = LassoLars(alpha=1, random_state = 825)
    # fit the model.
    lars.fit(X_train, y_train.colonies_lost)
    #predict on test
    y_test['colonies_lost_pred_lars'] = lars.predict(X_test)
    
    # evaluate: test rmse
    rmse_test= round(mean_squared_error(y_test.colonies_lost, y_test.colonies_lost_pred_lars,squared = False),2)
    rmse_baseline = round(mean_squared_error(y_train.colonies_lost,y_train.baseline_mean, squared = False),2)

    print(f'The RMSE on test dataset is {rmse_test} while RMSE on baseline is {rmse_baseline}.' )



def viz_test_perfomance(y_test):
    '''This function will plot the acutal target and prediction uisng best model'''
    plt.figure(figsize = (16,8))
    #plot actual target
    y_test.colonies_lost.hist(bins = 1000)
    #plot predicted targer
    plt.hist(y_test.colonies_lost_pred_lars, color='green', alpha=.7, label="Model:Lassolars", bins = 1000)
    #set x limit
    plt.xlim(0,1200)
    plt.title("model prediction in test data")
    plt.xlabel("colony lost")
    plt.ylabel("count")
    plt.legend()
    plt.show()



def get_baseline_RMSE(y_train,y_validate):
    '''
    this function will calculate baseline mean and baseline median and calculate RMSE from mean and median
    '''
    #get mean of target from train
    y_train["baseline_mean"] = y_train.colonies_lost.mean()
    #get median of target from train
    y_train["baseline_median"] =y_train.colonies_lost.median()
    #get mean of target from validate
    y_validate["baseline_mean"] = y_validate.colonies_lost.mean()
    #get median from target from validate
    y_validate["baseline_median"] =y_validate.colonies_lost.median()
    
    #calculate RMSE 
    RMSE_train_mean=mean_squared_error(y_train.colonies_lost,y_train.baseline_mean, squared = False)
    RMSE_validate_mean=mean_squared_error(y_validate.colonies_lost,y_validate.baseline_mean, squared = False)

    print("RMSE using Mean on \nTrain: ", round(RMSE_train_mean,2), "\nValidate: ", round(RMSE_validate_mean,2))
    print()

    #calculate RMSE
    RMSE_train_median= mean_squared_error(y_train.colonies_lost,y_train.baseline_median, squared = False)
    RMSE_validate_median= mean_squared_error(y_validate.colonies_lost,y_validate.baseline_median, squared = False)

    print("RMSE using Median on \nTrain: ", round(RMSE_train_median,2), "\nValidate: ", round(RMSE_validate_median,2))
    
    
def select_kbest(X,y,k):
    """This function will input two array X, y and number of top features K and outputs the top k number of features """
    #create the model
    kbest = SelectKBest(f_regression, k=k)
    #fit the model
    kbest.fit(X,y)
    #output the top features 
    features = X.columns[kbest.get_support()]
    
    return features


def select_rfe(X,y,  n_features_to_select = 4):
    """This function will input two array X, y and number of top features desired and outputs those features """
    #create the model
    rfe=RFE(LinearRegression(), n_features_to_select = n_features_to_select) 
    #fit the model
    rfe.fit(X,y)
    #output top features
    features = X.columns[rfe.get_support()]
    
    return features


def largest_loss(train):
    ''' This function will input train data and plot average colony loss by season each year and overall'''
    # set figure size
    #plt.figure(figsize=(16, 10))
    # plot colonies lost, grouped by year and month
    train.colonies_lost.groupby([train.index.year, train.index.month]).sum().unstack(0).plot(figsize = (14,10))
    #set average for each month
    avg_line = train.colonies_lost.groupby(train.index.month).sum()
    mean_line = avg_line / 10
    #plot mean line
    mean_line.plot(label='Average', color='red', linewidth=4, legend=True)
    # set title
    plt.title('Annual Colony Loss by Season', fontsize = 16)
    # set tick label formatting
    plt.ticklabel_format(style='plain', axis='y')
    # plot vertical line for summer
    plt.vlines(x=4, ymin=0, ymax=120000)
    # plot vertical line for winter
    plt.vlines(x=10, ymin=0, ymax=120000)
    # label vertical line for summer
    plt.annotate('Beginning of Summer', [3.8,121000], xycoords='data')
    # label vertical line for winter
    plt.annotate('Beginning of Winter', [9.0,121000], xycoords='data')
    # label x-axis
    plt.xlabel('Month')
    # label y-axis
    plt.ylabel('Colonies Lost')
    
    plt.show()

#==================== Grid Search ===============================

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

