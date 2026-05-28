from sklearn.ensemble import AdaBoostRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

models = dict(
    linear_reg=LinearRegression(normalize=True),
    decision_tree=DecisionTreeRegressor(random_state=1, max_depth=10, min_samples_split=10),
    adaboost=AdaBoostRegressor(random_state=1),
    gradboost=GradientBoostingRegressor(random_state=1),
    random_forest=RandomForestRegressor(random_state=1),
    extra_trees=ExtraTreesRegressor(bootstrap=False,
                                    max_features=0.7500000000000001,
                                    min_samples_leaf=1,
                                    min_samples_split=2,
                                    n_estimators=100),
    extra_trees2=ExtraTreesRegressor(bootstrap=True, max_features=0.6000000000000001,
                                     min_samples_leaf=1,
                                     min_samples_split=9,
                                     n_estimators=100),
    svm=SVR(gamma=0.00009, C=10, epsilon=0.2),
    xgboost=XGBRegressor(max_depth=9,
                         learning_rate=0.013,
                         n_estimators=2000,
                         silent=True,
                         nthread=-1,
                         gamma=0,
                         min_child_weight=1,
                         max_delta_step=0,
                         subsample=0.75,
                         colsample_bytree=0.85,
                         colsample_bylevel=1,
                         reg_alpha=0,
                         reg_lambda=1,
                         scale_pos_weight=1,
                         seed=1440,
                         missing=None)
)
