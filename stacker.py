__author__ = 'MSteger'

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, MetaEstimatorMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels, check_classification_targets


class stacker(BaseEstimator, ClassifierMixin):

    def __init__(self, layers = None, skf = None, average = False, verbose = 0):
        self.layers = layers
        self.skf = skf
        self.fitted = False
        self.average = average
        self.verbose = verbose > 0

    def _fit_layer(self, X, y, models, last_layer = False):
        layer_pred = np.zeros((X.shape[0], len(self.classes_) - 1 + last_layer, len(models)))
        if not self.fitted:
            for i, (train_idx, test_idx) in enumerate(self.skf.split(X, y)):
                for j, model in enumerate(models):
                    if self.verbose:print 'bin {}: fitting model {}\n'.format(i, type(model).__name__)
                    model.fit(X[train_idx], y[train_idx])
                    bin_pred = model.predict_proba(X[test_idx])[:, 1:]
                    layer_pred[test_idx, :, j] = bin_pred
        else:
            for j, model in enumerate(models):
                if self.verbose: print 'predicting model {}\n'.format(type(model).__name__)
                bin_pred = model.predict_proba(X)[:, not last_layer:]
                layer_pred[:, :, j] = bin_pred
        if self.average or last_layer: layer_pred = layer_pred.mean(axis = -1)
        if len(layer_pred.shape) > 2: layer_pred = layer_pred.reshape(layer_pred.shape[0], reduce(lambda x, y: x*y, layer_pred.shape[1:]))
        return layer_pred

    def _iterate_layers(self, X, y = None):
        for i, models in enumerate(self.layers):
            if self.verbose: print 'layer {}:'.format(i)
            X = self._fit_layer(X = X, y = y, models = models, last_layer = (i == len(self.layers) - 1)*self.fitted)
        return X

    def fit(self, X, y = None):
        X, y = check_X_y(X, y)
        check_classification_targets(y)
        self.classes_ = unique_labels(y)
        self._iterate_layers(X = X, y = y)
        self.fitted = True
        self.X_, self.y_ = X, y
        return self

    def predict(self, X):
        return self.predict_proba(X).argmax(axis = 1)

    def predict_proba(self, X):
        check_is_fitted(self, ['X_', 'y_'])
        X = check_array(X)
        X_pred = self._iterate_layers(X = X)
        return X_pred

if __name__ == '__main__':
    from sklearn.utils.estimator_checks import check_estimator
    from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
    # check_estimator(stacker) ## currently fails

    from xgboost import XGBClassifier
    layers = (
        (
            RandomForestClassifier(n_jobs = -1),
            ExtraTreesClassifier(n_jobs = -1),
            RandomForestClassifier(n_jobs = -1),

        ),
        (
            RandomForestClassifier(n_jobs = 1),
            ExtraTreesClassifier(n_jobs = -1)
        ),
        (
            XGBClassifier(n_jobs = -1),
            ExtraTreesClassifier(n_jobs = 1)
        )
    )

    numeric_cols = ['L1_S24_F1846', 'L3_S32_F3850', 'L1_S24_F1695', 'L1_S24_F1632',
                    'L3_S33_F3855', 'L1_S24_F1604',
                    'L3_S29_F3407', 'L3_S33_F3865',
                    'L3_S38_F3952', 'L1_S24_F1723',
                    ]

    import pandas as pd
    X = pd.read_csv('example/train.csv.gz', usecols=numeric_cols, index_col=0).fillna(6666666).astype(np.float32)
    y = pd.read_csv('example/Y.csv.gz', index_col=0)['Response'].astype(np.int8)

    from sklearn.model_selection import StratifiedKFold
    ensemble = stacker(layers = layers, skf = StratifiedKFold(n_splits = 2, shuffle = True))
    ensemble.fit(X = X.as_matrix()[:5000], y = y.as_matrix()[:5000])
    yhat = ensemble.predict_proba(X.as_matrix()[5000:10000])

    from sklearn.metrics import accuracy_score
    print accuracy_score(y[5000:10000], yhat.argmax(axis = 1))
    print 'done'