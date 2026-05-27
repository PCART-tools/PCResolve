import wrangle
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error,explained_variance_score
from sklearn.linear_model import LinearRegression,LassoLars,TweedieRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error,explained_variance_score


def split_data(df):
    '''This function will input dataframe and split into train,validate,test'''
    #split dataframw into 80% train  and 20% test 
    train_validate, test = train_test_split(df, test_size=.2, random_state=825)
     #split train further into 75% train, 25% validate
    train, validate = train_test_split(train_validate, test_size=.25, random_state=825)
    
    #return train,validate,test back to function
    return train,validate,test


def scale_data(train,validate,test,columns):
    #make the scaler
    scaler = MinMaxScaler()
    #fit the scaler at train data only
    scaler.fit(train[columns])
    #tranforrm train, validate and test
    train_scaled = scaler.transform(train[columns])
    validate_scaled = scaler.transform(validate[columns])
    test_scaled = scaler.transform(test[columns])
    
    # Generate a list of the new column names with _scaled added on
    scaled_columns = [col+"_scaled" for col in columns]
    
    #concatenate with orginal train, validate and test
    scaled_train = pd.concat([train.reset_index(drop = True),pd.DataFrame(train_scaled,columns = scaled_columns)],axis = 1)
    scaled_validate = pd.concat([validate.reset_index(drop = True),pd.DataFrame(validate_scaled, columns = scaled_columns)], axis = 1)
    scaled_test= pd.concat([test.reset_index(drop = True),pd.DataFrame(test_scaled,columns = scaled_columns)],axis = 1)
    
    return scaled_train,scaled_validate,scaled_test


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


def get_RMSE(X_train,y_train, X_validate, y_validate):
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
    'model': 'OLS Regressor', 
    'RMSE_train': rmse_train_lm,
    'RMSE_validate': rmse_validate_lm,
    }, ignore_index=True)
    
    
    # create the model object
    lars = LassoLars(alpha=1)
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
    'model': 'LASSOLARS(alpha = 1)', 
    'RMSE_train': rmse_train_lars,
    'RMSE_validate': rmse_validate_lars,
    }, ignore_index=True)
    
    
    
    # create the model object
    glm = TweedieRegressor(power=1, alpha=0)
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
    'model': 'Tweedie Regressor(power=1, alpha=0)', 
    'RMSE_train': rmse_train_tw,
    'RMSE_validate': rmse_validate_tw,
    }, ignore_index=True)
    
    
    
    
    #create model object
    pf= PolynomialFeatures(degree= 5)
    # fit and transform X_train_scaled
    X_train_degree5 = pf.fit_transform(X_train)
    # transform X_validate_scaled 
    X_validate_degree5 = pf.transform(X_validate)

    # create the model object
    lm5 = LinearRegression(normalize=True)
    # fit the model to our training data. We must specify the column in y_train,  
    lm5.fit(X_train_degree5, y_train.colonies_lost)
    # predict train
    y_train['colonies_lost_pred_lm5'] = lm5.predict(X_train_degree5)
    # predict validate
    y_validate['colonies_lost_pred_lm5'] = lm5.predict(X_validate_degree5)

    # evaluate: train rmse
    rmse_train_py= round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pred_lm5, squared = False),2)
    # evaluate: validate rmse
    rmse_validate_py= round(mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lost_pred_lm5, squared = False) , 2)

    #append model and RMSE from Polynomial Regression model to metric dataframe
    metric_df = metric_df.append({
    'model': 'Polynomial Regression(degree = 5)', 
    'RMSE_train': rmse_train_py,
    'RMSE_validate': rmse_validate_py,
    }, ignore_index=True)
    
    
    print(metric_df)