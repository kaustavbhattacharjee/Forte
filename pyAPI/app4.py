from cmath import nan
from tracemalloc import start
from flask import Flask, render_template, Response, g, redirect, url_for, request,jsonify, make_response, send_from_directory
import time, os, re, random, calendar
import pandas as pd
import numpy as np
from flask_cors import CORS
import requests, ast, statistics
import json 
from tqdm import tqdm# as tqdm1
import logging
import tensorflow as tf
import tensorflow_probability as tfp
from tensorflow.keras import backend as K
import math
from scipy import io
from scipy.io import loadmat
from tensorflow import keras
from tensorflow.keras import layers
from keras.layers import Input, Dense, LSTM, Reshape, Conv1D, MaxPooling1D, Flatten,UpSampling1D,Conv1DTranspose
from keras.models import Model
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
import properscoring as ps
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from apiflask import APIFlask, Schema, abort
from apiflask.fields import Integer, String, List
from apiflask.validators import Length, OneOf, Range
import shap



pd.options.mode.chained_assignment = None  # default='warn'

app = APIFlask(__name__)
CORS(app)
logging.basicConfig(filename='pyAPI/logs/flask.log',level=logging.DEBUG,format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s') #https://www.scalyr.com/blog/getting-started-quickly-with-flask-logging/
path_parent = os.getcwd()
np.random.seed(7)
tf.random.set_seed(7)


### Utility functions ###

class Scaler1D:
    """
    Utility class for sequence scaling
    """
    def fit(self, X):
        np.random.seed(7)
        tf.random.set_seed(7)
        self.mean = np.nanmean(np.asarray(X).ravel())
        self.std = np.nanstd(np.asarray(X).ravel())
        return self
        
    def transform(self, X):
        return (X - np.min(X,0))/(np.max(X,0)-np.min(X,0))
    
    def inverse_transform(self, X):
        return X*(np.max(X,0)-np.min(X,0)) + np.min(X,0)

sequence_length = 24*2
def gen_seq(id_df, seq_length, seq_cols):
    """
    This function converts the dataframe into numpy array of arrays
    Inputs:
    id_df: dataframe
    seq_length: length of historical datapoints to use for forecast
    seq_cols: columns of the dataframe id_df

    Output:
    numpy array of arrays for each sequence
    Example:
    Sequence 1 would be the df rows (0,48)
    Sequence 2 would be the df rows (1,49)
    Sequence 3 would be the df rows (2,50)
    ...
    Sequence n would be the df rows (26180,26228)
    """
    data_matrix =  id_df[seq_cols]
    num_elements = data_matrix.shape[0]

    for start, stop in zip(range(0, num_elements-seq_length, 1), range(seq_length, num_elements, 1)):
        
        yield data_matrix[stop-sequence_length:stop].values.reshape((-1,len(seq_cols)))
def gen_seq1(id_df, seq_length, seq_cols):
    """
    This function converts the dataframe into numpy array of arrays
    Inputs:
    id_df: dataframe
    seq_length: length of historical datapoints to use for forecast
    seq_cols: columns of the dataframe id_df

    Output:
    numpy array of arrays for each sequence
    Example:
    Sequence 1 would be the df rows (0,48)
    Sequence 2 would be the df rows (1,49)
    Sequence 3 would be the df rows (2,50)
    ...
    Sequence n would be the df rows (26180,26228)
    """
    data_matrix =  id_df[seq_cols]
    num_elements = data_matrix.shape[0]

    for start, stop in zip(range(0, num_elements-seq_length, 1), range(seq_length, num_elements, 1)):
        
        yield data_matrix[stop-seq_length:stop].values.reshape((-1,len(seq_cols)))
def NLL(y, distr): 
    sy = distr.mean()
    return 1*-distr.log_prob(y)+tf.keras.losses.mean_squared_error(y, sy)

def kernel(x, y):
    return math.exp(-np.linalg.norm(x - y)/2)

# Defining APE Formulae
def calculate_ape(y_true, y_pred):
    y_true, y_pred = (y_true.flatten()).tolist(), (y_pred.flatten()).tolist()
    ape_array = []
    for i in range(len(y_true)):
        ape_array.append(abs((y_true[i] - y_pred[i]) / y_true[i]) * 100)
    return ape_array

#deprecated
def kPF_func_calculation(solar_penetration):
    nsamples = 10000
    gamma = 10
    A = np.load(path_parent+"/data/models/pen_"+str(solar_penetration)+"/dict.npy", allow_pickle=True).item()
    #A = np.load("dict.npy", allow_pickle=True).item()
    Kinv = A['kinv']
    L = A['L']
    z = A['z']
    x = A['x']
    ntrain = x.shape[0]
    latent_dim = x.shape[1]
    nz = np.random.multivariate_normal(np.zeros((latent_dim,)), np.eye(latent_dim), nsamples)

    nv = np.zeros((ntrain, nsamples))
    for i in range(ntrain):
        for j in range(nsamples):
            nv[i][j] = kernel(z[i], nz[j])
    s = L@Kinv@nv   #matrix multiplication
    ind = np.argsort(-s, 0)[:gamma,:]
    latent_gen = np.zeros((nsamples, latent_dim))
    for i in range(nsamples):
        _sum = 0
        for j in range(gamma):
            latent_gen[i] += s[ind[j][i]][i] * x[ind[j][i]]
            _sum += s[ind[j][i]][i]
        latent_gen[i] /= _sum
    #print(latent_gen)
    return latent_gen

def pbb_calculation(obs, pred):
    mean = np.mean(pred)
    sd = np.std(pred)
    upper_bound = mean + sd
    lower_bound = mean -sd
    pbb = ((len(list(x for x in obs if lower_bound < x < upper_bound)))/len(obs))*100
    return pbb

### Loading the models ###
t = time.process_time()
print("#### Models and data loading: Started ####")
autoencoder_models, encoder_models, lstm_models, latent_gens = {}, {}, {}, {}
solar_penetration_levels = ["0","10","20","50"]
for i in solar_penetration_levels:
    autoencoder_models[i] = tf.keras.models.load_model(path_parent+"/data/models/pen_"+i+"/autoencoder.h5")
    encoder_models[i] = tf.keras.models.load_model(path_parent+"/data/models/pen_"+i+"/encoder.h5")
    lstm_models[i] = tf.keras.models.load_model(path_parent+"/data/models/pen_"+i+"/model_rnn_probab_nonsol.h5", custom_objects={'NLL': NLL})
    latent_gens[i] = np.load(path_parent+"/data/models/pen_"+i+"/latent_gen.npy")
elapsed_time_model_load = time.process_time() - t
loading_message = "#### Models and data loading: Completed in %f seconds or %f minutes ####" %(elapsed_time_model_load, (elapsed_time_model_load/60))
print(loading_message)
app.logger.info(loading_message)

t = time.process_time()
print("#### Models and data loading for v1.4: Started ####")
autoencoder_models_1_4, encoder_models_1_4, lstm_models_1_4, mu_models_1_4, latent_gens_1_4 = {}, {}, {}, {}, {}
solar_penetration_levels = ["20"]
for i in solar_penetration_levels:
    autoencoder_models_1_4[i] = tf.keras.models.load_model(path_parent+"/data/models/v1.4/pen_"+i+"/autoencoder.h5")
    encoder_models_1_4[i] = tf.keras.models.load_model(path_parent+"/data/models/v1.4/pen_"+i+"/encoder.h5")
    lstm_models_1_4[i] = tf.keras.models.load_model(path_parent+"/data/models/v1.4/pen_"+i+"/model_rnn_probab_nonsol.h5")
    mu_models_1_4[i] = tf.keras.models.load_model(path_parent+"/data/models/v1.4/pen_"+i+"/mu_model.h5")
    latent_gens_1_4[i] = np.load(path_parent+"/data/models/v1.4/pen_"+i+"/latent_gen.npy")
elapsed_time_model_load = time.process_time() - t
loading_message = "#### Models and data loading for v1.4: Completed in %f seconds or %f minutes ####" %(elapsed_time_model_load, (elapsed_time_model_load/60))
print(loading_message)
app.logger.info(loading_message)

### Pipeline functions and others (non-callable externally) ###
def prepare_general_input(start_date, end_date, solar_penetration, updated_metric):
    t = time.process_time()
    print("times in general input: ", start_date, end_date)
    A=pd.read_csv(path_parent+"/data/inputs/df1_solar_"+str(solar_penetration)+"_pen.csv") # Reading file
    my_data = A.loc[(A['min_t'] >= start_date) & (A['min_t'] < end_date)]
    my_data.reset_index(inplace=True, drop=True)
    temperature_nans = (my_data['temp'].apply(np.isnan)).tolist() # getting a list with index positions of NaNs
    humidity_nans = (my_data['humidity'].apply(np.isnan)).tolist()
    apparent_power_nans = (my_data['apparent_power'].apply(np.isnan)).tolist()
    temperature_nans_percentage = (sum(temperature_nans)/len(temperature_nans))*100 #counting the percentage of NaNs in data
    humidity_nans_percentage = (sum(humidity_nans)/len(humidity_nans))*100
    apparent_power_nans_percentage = (sum(apparent_power_nans)/len(apparent_power_nans))*100
    #my_data=my_data.fillna(99999)
    # Injecting updated temperature
    temperature_column =[]
    if(len(updated_metric["temperature"])>0):
        for item in updated_metric["temperature"]: temperature_column.append(item[3])
        # print("Temperature was increased ", temperature_column[0])
        my_data['temp'] = temperature_column
    else: temperature_column = my_data['temp'].tolist()
    # Injecting updated humidity
    humidity_column =[]
    if(len(updated_metric["humidity"])>0):
        for item in updated_metric["humidity"]: humidity_column.append(item[3])
        my_data['humidity'] = humidity_column
    else: humidity_column = my_data['humidity'].tolist()    
    # Injecting updated apparent_power
    apparent_power_column =[]
    if(len(updated_metric["apparent_power"])>0):
        for item in updated_metric["apparent_power"]: apparent_power_column.append(item[3])
        my_data['apparent_power'] = apparent_power_column 
    else: apparent_power_column = my_data['apparent_power'].tolist()               
    my_data = my_data.interpolate(method="linear", axis=0, limit_direction='both') # linear interpolation column by column; both directions so that the first and last columns are not left alone
    #my_data = A
    print("my data ", my_data.shape)
    timeline = my_data['min_t'].to_list() # capturing the timeline called
    timeline_original = timeline
    temperature_original = my_data['temp'].to_list() # capturing the original temperature
    humidity_original = my_data['humidity'].to_list() # capturing the original temperature
    apparent_power_original = my_data['apparent_power'].to_list() # capturing the original temperature
    #temperature_original = [99999 if math.isnan(item) else item for item in temperature_original]
    timeline = timeline[48:] # removing the first 48 entries(i.e., 12 hours)
    my_data=my_data.drop(['min_t'], axis=1) # Drop this axis
    #my_data=my_data.fillna(99999)

    # Creating a df for updated_metric
    df_updated_metric = pd.DataFrame({
        "timeline_original": timeline_original,
        "updated_temperature": temperature_column,
        "updated_humidity": humidity_column,
        "updated_apparent_power": apparent_power_column
    })

    sequence_length = 24*2 # Length of historical datapoints to use for forecast
    sequence_input = []
    for seq in tqdm(gen_seq(my_data, sequence_length, my_data.columns)):
        sequence_input.append(seq)    
    sequence_input = np.asarray(sequence_input) 
    #print("sequence_input ", sequence_input)
    
    # y_ground=[]
    # for i in range(len(sequence_input)):
    #     y_ground.append(my_data.iloc[i+48]['power'])   # Original code
    #     #y_ground.append(my_data.iloc[i]['power'])   
    # y_ground=np.asarray(y_ground)
    #pd.DataFrame(y_ground).to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_ground.csv", header=None, index=None)

    temperature = []
    for i in range(len(sequence_input)):
        temperature.append(my_data.iloc[i+48]['temp'])
    humidity = []
    for i in range(len(sequence_input)):
        humidity.append(my_data.iloc[i+48]['humidity'])
    apparent_power = []
    for i in range(len(sequence_input)):
        apparent_power.append(my_data.iloc[i+48]['apparent_power'])        
  

    # y_prev = []
    # sequence_target = []
    # #AA=A
    # B=my_data.drop(['apparent_power', 'humidity','temp'], axis=1)
    # for seq in tqdm(gen_seq(B, sequence_length, B.columns)):
    #     y_prev.append(seq)
    # y_prev=np.asarray(y_prev)
    # print("y_prev", y_prev)
    # y_prev=y_prev.reshape((y_prev.shape[0],y_prev.shape[1]))
    elapsed_time_prepare_input = time.process_time() - t
    return  temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original, df_updated_metric

def prepare_input(start_date, end_date, solar_penetration, updated_metric, df_updated_metric):
    t = time.process_time()
    A=pd.read_csv(path_parent+"/data/inputs/df1_solar_"+str(solar_penetration)+"_pen.csv") # Reading file
    my_data = A.loc[(A['min_t'] >= start_date) & (A['min_t'] < end_date)]
    my_data.reset_index(inplace=True, drop=True)

    my_df_updated_metric = df_updated_metric.loc[(df_updated_metric['timeline_original'] >= start_date) & (df_updated_metric['timeline_original'] < end_date)]
    my_df_updated_metric.reset_index(inplace=True, drop=True)
    # print("my_df column type: ", my_df_updated_metric.timeline_original.dtype, " my_data column type: ", my_data.min_t.dtype)
    # print("my_df shape: ", my_df_updated_metric.shape, "my data shape: ", my_data.shape)
    # print(my_df_updated_metric)
    # print(my_data)
    my_data.set_index('min_t')
    my_df_updated_metric.set_index('timeline_original')
    # temperature_nans = (my_data['temp'].apply(np.isnan)).tolist() # getting a list with index positions of NaNs
    # humidity_nans = (my_data['humidity'].apply(np.isnan)).tolist()
    # apparent_power_nans = (my_data['apparent_power'].apply(np.isnan)).tolist()
    # temperature_nans_percentage = (sum(temperature_nans)/len(temperature_nans))*100 #counting the percentage of NaNs in data
    # humidity_nans_percentage = (sum(humidity_nans)/len(humidity_nans))*100
    # apparent_power_nans_percentage = (sum(apparent_power_nans)/len(apparent_power_nans))*100
    #my_data=my_data.fillna(99999)

    ## Commenting out for now
    # Injecting updated temperature
    temperature_column =[]
    if(len(updated_metric["temperature"])>0): # Read from my_df_updated_metric only if there is an update; else there would be NaN values
        temperature_column = my_df_updated_metric["updated_temperature"].to_list()
        #for item in updated_metric["temperature"]: temperature_column.append(item[3])
        # print("Temperature was increased ", temperature_column[0])
        my_data2 = my_data
        my_data.loc[my_df_updated_metric.index, 'temp'] = my_df_updated_metric["updated_temperature"]
        #my_data['temp'] = temperature_column
    # Injecting updated humidity
    humidity_column =[]
    if(len(updated_metric["humidity"])>0):
        # for item in updated_metric["humidity"]: humidity_column.append(item[3])
        # my_data['humidity'] = humidity_column
        my_data.loc[my_df_updated_metric.index, 'humidity'] = my_df_updated_metric["updated_humidity"]
    # Injecting updated apparent_power
    apparent_power_column =[]
    if(len(updated_metric["apparent_power"])>0):
        # for item in updated_metric["apparent_power"]: apparent_power_column.append(item[3])
        # my_data['apparent_power'] = apparent_power_column    
        my_data.loc[my_df_updated_metric.index, 'apparent_power'] = my_df_updated_metric["updated_apparent_power"]        
    my_data = my_data.interpolate(method="linear", axis=0, limit_direction='both') # linear interpolation column by column; both directions so that the first and last columns are not left alone
    #my_data = A
    print("my data ", my_data.shape)
    timeline = my_data['min_t'].to_list() # capturing the timeline called
    # timeline_original = timeline
    # temperature_original = my_data['temp'].to_list() # capturing the original temperature
    # humidity_original = my_data['humidity'].to_list() # capturing the original temperature
    # apparent_power_original = my_data['apparent_power'].to_list() # capturing the original temperature
    #temperature_original = [99999 if math.isnan(item) else item for item in temperature_original]
    timeline = timeline[48:] # removing the first 48 entries(i.e., 12 hours)
    my_data=my_data.drop(['min_t'], axis=1) # Drop this axis
    #my_data=my_data.fillna(99999)

    sequence_length = 24*2 # Length of historical datapoints to use for forecast
    sequence_input = []
    for seq in tqdm(gen_seq(my_data, sequence_length, my_data.columns)):
        sequence_input.append(seq)    
    sequence_input = np.asarray(sequence_input) 
    print("sequence_input ", sequence_input)
    
    y_ground=[]
    for i in range(len(sequence_input)):
        y_ground.append(my_data.iloc[i+48]['power'])   # Original code
        #y_ground.append(my_data.iloc[i]['power'])   
    y_ground=np.asarray(y_ground)
    #pd.DataFrame(y_ground).to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_ground.csv", header=None, index=None)

    temperature = []
    for i in range(len(sequence_input)):
        temperature.append(my_data.iloc[i+48]['temp'])
    humidity = []
    for i in range(len(sequence_input)):
        humidity.append(my_data.iloc[i+48]['humidity'])
    apparent_power = []
    for i in range(len(sequence_input)):
        apparent_power.append(my_data.iloc[i+48]['apparent_power'])        
  

    y_prev = []
    sequence_target = []
    #AA=A
    B=my_data.drop(['apparent_power', 'humidity','temp'], axis=1)
    for seq in tqdm(gen_seq(B, sequence_length, B.columns)):
        y_prev.append(seq)
    y_prev=np.asarray(y_prev)
    print("y_prev", y_prev)
    y_prev=y_prev.reshape((y_prev.shape[0],y_prev.shape[1]))
    elapsed_time_prepare_input = time.process_time() - t
    #return sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original
    return sequence_input, y_ground, y_prev


def prepare_input0(start_date, end_date, solar_penetration, updated_metric):
    t = time.process_time()
    A=pd.read_csv(path_parent+"/data/inputs/df1_solar_"+str(solar_penetration)+"_pen.csv") # Reading file
    my_data = A.loc[(A['min_t'] >= start_date) & (A['min_t'] < end_date)]
    my_data.reset_index(inplace=True, drop=True)
    temperature_nans = (my_data['temp'].apply(np.isnan)).tolist() # getting a list with index positions of NaNs
    humidity_nans = (my_data['humidity'].apply(np.isnan)).tolist()
    apparent_power_nans = (my_data['apparent_power'].apply(np.isnan)).tolist()
    temperature_nans_percentage = (sum(temperature_nans)/len(temperature_nans))*100 #counting the percentage of NaNs in data
    humidity_nans_percentage = (sum(humidity_nans)/len(humidity_nans))*100
    apparent_power_nans_percentage = (sum(apparent_power_nans)/len(apparent_power_nans))*100
    #my_data=my_data.fillna(99999)
    # Injecting updated temperature
    temperature_column =[]
    if(len(updated_metric["temperature"])>0):
        for item in updated_metric["temperature"]: temperature_column.append(item[3])
        # print("Temperature was increased ", temperature_column[0])
        my_data['temp'] = temperature_column
    # Injecting updated humidity
    humidity_column =[]
    if(len(updated_metric["humidity"])>0):
        for item in updated_metric["humidity"]: humidity_column.append(item[3])
        my_data['humidity'] = humidity_column
    # Injecting updated apparent_power
    apparent_power_column =[]
    if(len(updated_metric["apparent_power"])>0):
        for item in updated_metric["apparent_power"]: apparent_power_column.append(item[3])
        my_data['apparent_power'] = apparent_power_column            
    my_data = my_data.interpolate(method="linear", axis=0, limit_direction='both') # linear interpolation column by column; both directions so that the first and last columns are not left alone
    #my_data = A
    timeline = my_data['min_t'].to_list() # capturing the timeline called
    timeline_original = timeline
    temperature_original = my_data['temp'].to_list() # capturing the original temperature
    humidity_original = my_data['humidity'].to_list() # capturing the original temperature
    apparent_power_original = my_data['apparent_power'].to_list() # capturing the original temperature
    #temperature_original = [99999 if math.isnan(item) else item for item in temperature_original]
    timeline = timeline[48:] # removing the first 48 entries(i.e., 12 hours)
    my_data=my_data.drop(['min_t'], axis=1) # Drop this axis
    #my_data=my_data.fillna(99999)

    sequence_length = 24*2 # Length of historical datapoints to use for forecast
    sequence_input = []
    for seq in gen_seq(my_data, sequence_length, my_data.columns):
        sequence_input.append(seq)    
    sequence_input = np.asarray(sequence_input) 
    #print(sequence_input)
    
    y_ground=[]
    for i in range(len(sequence_input)):
        y_ground.append(my_data.iloc[i+48]['power'])   # Original code
        #y_ground.append(my_data.iloc[i]['power'])   
    y_ground=np.asarray(y_ground)
    #pd.DataFrame(y_ground).to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_ground.csv", header=None, index=None)

    temperature = []
    for i in range(len(sequence_input)):
        temperature.append(my_data.iloc[i+48]['temp'])
    humidity = []
    for i in range(len(sequence_input)):
        humidity.append(my_data.iloc[i+48]['humidity'])
    apparent_power = []
    for i in range(len(sequence_input)):
        apparent_power.append(my_data.iloc[i+48]['apparent_power'])        
  

    y_prev = []
    sequence_target = []
    #AA=A
    B=my_data.drop(['apparent_power', 'humidity','temp'], axis=1)
    for seq in gen_seq(B, sequence_length, B.columns):
        y_prev.append(seq)
    y_prev=np.asarray(y_prev)
    y_prev=y_prev.reshape((y_prev.shape[0],y_prev.shape[1]))
    elapsed_time_prepare_input = time.process_time() - t
    return sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original

def autoencoder_func(sequence_input, solar_penetration):
    t = time.process_time()
    scaler_target = Scaler1D().fit(sequence_input)
    seq_inp_norm = scaler_target.transform(sequence_input)
    #pred_train=autoencoder_model.predict(seq_inp_norm) # this one does not work
    encoder_model = encoder_models[str(solar_penetration)]
    pred_train=encoder_model.predict(seq_inp_norm)
    #print(pred_train)
    #pd.DataFrame(pred_train).to_csv(path_parent+'/data/outputs/pen_"+str(solar_penetration)+"/pred_train.csv', header=None, index=None)
    elapsed_time_autoencoder = time.process_time() - t
    return pred_train, elapsed_time_autoencoder

def kPF_func(pred_train, solar_penetration):
    t = time.process_time()
    latent_gen = latent_gens[str(solar_penetration)]
    elapsed_time_kpf = time.process_time() - t
    return latent_gen, elapsed_time_kpf

def lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration):
    t = time.process_time()
    aa = (latent_gen)
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in range(total_train):
        yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    scaler_target = Scaler1D().fit(total_train_data)
    total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
    Y=total_norm_train[:,41]

    lstm_model = lstm_models[str(solar_penetration)]
    y_pred = lstm_model.predict(X)
    y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    #y_pred = y_pred.flatten()
    #print(y_pred, Y_test)

    # Un comment for old way of calculating confidence interval
    # mean = lambda x: x.mean()#.flatten()
    # sd = lambda x: x.std()#.flatten() 
    # conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
    # two_sd = 2*sd(y_pred)
    # lower_y_pred = y_pred - two_sd
    # higher_y_pred = y_pred + two_sd

    func = K.function([lstm_model.get_layer(index=0).input], lstm_model.get_layer(index=6).output)
    layerOutput = func(X)  # input_data is a numpy array
    print(layerOutput.shape)
    y_pred = y_pred.flatten()
    conf_array_higher_limit, conf_array_lower_limit = [], []
    for index, concatenated_data in enumerate(layerOutput): # concatenated_data = [mean, sd]
        # sigma_sign = 1
        # if(concatenated_data[1]<0): sigma_sign = -1
        # sigma = sigma_sign * np.sqrt(abs(concatenated_data[1]))
        sigma = concatenated_data[1]
        lower_limit = y_pred[index] - 2*sigma
        higher_limit = y_pred[index] + 2*sigma
        conf_array_lower_limit.append(lower_limit) #reversing
        conf_array_higher_limit.append(higher_limit)
    lower_y_pred = np.array(conf_array_lower_limit) #y_pred - two_sd
    higher_y_pred = np.array(conf_array_higher_limit) #y_pred + two_sd
    
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = mean_absolute_error(Y_test, y_pred)
    mape = mean_absolute_percentage_error(Y_test, y_pred)
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    mse = mean_squared_error(Y_test, y_pred)
    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm

def lstm_func2(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration):
    t = time.process_time()
    aa = (latent_gen)
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in tqdm(range(total_train)):
        yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    scaler_target = Scaler1D().fit(total_train_data)
    total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
    Y=total_norm_train[:,41]

    lstm_model = lstm_models[str(solar_penetration)]
    y_pred = lstm_model.predict(X)
    #print(y_pred)
    y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])

    # Extracting the output of the concatenation layer (source: https://stackoverflow.com/a/65288168/13125348)
    func = K.function([lstm_model.get_layer(index=0).input], lstm_model.get_layer(index=6).output)
    layerOutput = func(X)  # input_data is a numpy array
    print(layerOutput.shape)
    y_pred = y_pred.flatten()
    conf_array_higher_limit, conf_array_lower_limit = [], []
    for index, concatenated_data in enumerate(layerOutput): # concatenated_data = [mean, sd]
        # sigma_sign = 1
        # if(concatenated_data[1]<0): sigma_sign = -1
        # sigma = sigma_sign * np.sqrt(abs(concatenated_data[1]))
        sigma = concatenated_data[1]
        lower_limit = y_pred[index] - 2*sigma
        higher_limit = y_pred[index] + 2*sigma
        conf_array_lower_limit.append(lower_limit) #reversing
        conf_array_higher_limit.append(higher_limit)
    #y_pred = y_pred.flatten()
    #print(y_pred, Y_test)
    # mean = lambda x: x.mean()#.flatten()
    # sd = lambda x: x.std()#.flatten() 
    # conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
    # two_sd = 2*sd(y_pred)
    # lower_y_pred = y_pred + conf_int_95[0]
    # higher_y_pred = y_pred + conf_int_95[1]
    lower_y_pred = np.array(conf_array_lower_limit) #y_pred - two_sd
    higher_y_pred = np.array(conf_array_higher_limit) #y_pred + two_sd
    #print("Conf", conf_int_95)
    # np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    # np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    # np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    # np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = 0 # mean_absolute_error(Y_test, y_pred)
    mape = 0 # mean_absolute_percentage_error(Y_test, y_pred)
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    #mse = mean_squared_error(Y_test, y_pred)
    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, elapsed_time_lstm

def lstm_func_shap1(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration):
    t = time.process_time()
    aa = (latent_gen)
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in range(total_train):
        yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    scaler_target = Scaler1D().fit(total_train_data)
    total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
    Y=total_norm_train[:,41]

    X_train=X[0:int(X.shape[0]*0.8),:,:]
    Y_train=Y[0:int(X.shape[0]*0.8)]

    lstm_model = lstm_models[str(solar_penetration)]
    y_pred = lstm_model.predict(X)
    y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    #y_pred = y_pred.flatten()
    #print(y_pred, Y_test)
    mean = lambda x: x.mean()#.flatten()
    sd = lambda x: x.std()#.flatten() 
    conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
    two_sd = 2*sd(y_pred)
    # lower_y_pred = y_pred + conf_int_95[0]
    # higher_y_pred = y_pred + conf_int_95[1]
    lower_y_pred = y_pred - two_sd
    higher_y_pred = y_pred + two_sd
    #print("Conf", conf_int_95)
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = mean_absolute_error(Y_test, y_pred)
    mape = mean_absolute_percentage_error(Y_test, y_pred)
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    mse = mean_squared_error(Y_test, y_pred)
    # SHAP
    print(X.shape)
    item_mega = []
    for item in X:
        sub_item_mega = []
        for sub_item in item:
            sub_item_mega.append(sub_item[0])
        test_item = np.array(sub_item_mega, dtype=np.float32)
        item_mega.append(test_item)
    item_mega = np.array(item_mega, dtype=np.float32)
    print(item_mega)
    #print(y_pred, y_pred.shape)
    def dummy_func(my_model, my_input):
        #Convert item_mega into X
        # pass X into lstm_model
        y_pred_shap = lstm_model.predict(X)
        y_pred_shap_ = [item[0] for item in y_pred_shap]
        y_pred_shap_ = np.array(y_pred_shap_, dtype=np.float32)
        # get the output
        # convert the output into item_mega format
        return y_pred_shap_
    # class new_model(lstm_model):
    #     def __init__(self):
    #         super().__init__()
    #         self.value1 = "Inside copy model"
    #     def call(self, input_tensor, training=False, **kwargs):
    #         # forward pass
    #         pass
    #     def build_graph(self, raw_shape): 
    #         pass    
    #     def predict(self, X, **kwargs):
    #         ans = super().predict(X) 
    #         ans_ = [item[0] for item in ans]
    #         ans_ = np.array(ans_, dtype=np.float32) 
    #         return ans_ 
    # nm = new_model(lstm_model)
    # print(nm.predict(X))

    explainer = shap.DeepExplainer(lstm_model, item_mega)
    shap_values = explainer.shap_values(item_mega)

    print(shap_values)

    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm

# def lstm_func_1_2x1(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration,y_pred_ground_truth):
#     t = time.process_time()
#     aa = (latent_gen)
#     #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
#     total_train=int(len(sequence_input))
#     yyy=np.zeros((total_train,40))
#     for index in range(total_train):
#         yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
#         yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
#     yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

#     y_train_sol=y_ground
#     total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
#     scaler_target = Scaler1D().fit(total_train_data)
#     total_norm_train = scaler_target.transform(total_train_data)
#     X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
#     Y=total_norm_train[:,41]

#     lstm_model = lstm_models[str(solar_penetration)]
#     y_pred = lstm_model.predict(X)
#     y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
#     Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
#     #y_pred = y_pred.flatten()
#     #print(y_pred, Y_test)
#     mean = lambda x: x.mean()#.flatten()
#     sd = lambda x: x.std()#.flatten() 
#     conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
#     two_sd = 2*sd(y_pred)
#     # lower_y_pred = y_pred + conf_int_95[0]
#     # higher_y_pred = y_pred + conf_int_95[1]
#     lower_y_pred = y_pred - two_sd
#     higher_y_pred = y_pred + two_sd
#     #print("Conf", conf_int_95)
#     #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
#     #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
#     #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
#     #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
#     mae = mean_absolute_error(y_pred_ground_truth, y_pred)
#     mape = mean_absolute_percentage_error(y_pred_ground_truth, y_pred)
#     # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
#     # pbb = pbb_calculation(Y_test, y_pred.flatten())
#     mse = mean_squared_error(Y_test, y_pred)
#     elapsed_time_lstm = time.process_time() - t
#     #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
#     return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm

def lstm_func_1_3(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration):
    t = time.process_time()
    aa = (latent_gen)
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in range(total_train):
        yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    scaler_target = Scaler1D().fit(total_train_data)
    total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
    Y=total_norm_train[:,41]

    lstm_model = lstm_models[str(solar_penetration)]
    y_pred = lstm_model.predict(X)
    y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    #y_pred = y_pred.flatten()
    #print(y_pred, Y_test)

    # Un comment for old way of calculating confidence interval
    # mean = lambda x: x.mean()#.flatten()
    # sd = lambda x: x.std()#.flatten() 
    # conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
    # two_sd = 2*sd(y_pred)
    # lower_y_pred = y_pred - two_sd
    # higher_y_pred = y_pred + two_sd

    func = K.function([lstm_model.get_layer(index=0).input], lstm_model.get_layer(index=6).output)
    layerOutput = func(X)  # input_data is a numpy array
    print(layerOutput.shape)
    y_pred = y_pred.flatten()
    conf_array_higher_limit, conf_array_lower_limit = [], []
    for index, concatenated_data in enumerate(layerOutput): # concatenated_data = [mean, sd]
        # sigma_sign = 1
        # if(concatenated_data[1]<0): sigma_sign = -1
        # sigma = sigma_sign * np.sqrt(abs(concatenated_data[1]))
        sigma = concatenated_data[1]
        lower_limit = y_pred[index] - 2*sigma
        higher_limit = y_pred[index] + 2*sigma
        conf_array_lower_limit.append(lower_limit) #reversing
        conf_array_higher_limit.append(higher_limit)
    lower_y_pred = np.array(conf_array_lower_limit) #y_pred - two_sd
    higher_y_pred = np.array(conf_array_higher_limit) #y_pred + two_sd
    
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = mean_absolute_error(Y_test, y_pred)
    mape = mean_absolute_percentage_error(Y_test, y_pred)
    ape_array = calculate_ape(Y_test[np.where(Y_test!=0)],y_pred[np.where(Y_test!=0)])
    mean_ape = statistics.mean(ape_array)
    median_ape = statistics.median(ape_array)
    mode_ape = statistics.mode(ape_array)
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    mse = mean_squared_error(Y_test, y_pred)
    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, mean_ape, median_ape, mode_ape, elapsed_time_lstm



def prepare_input_1_4(start_date, end_date, solar_penetration, updated_metric, metrics):
    t = time.process_time()
    #A=pd.read_csv(path_parent+"/data/inputs/df1_solar_"+str(solar_penetration)+"_pen.csv") # Reading file
    A=pd.read_csv(path_parent+"/data/inputs/v1.4/input_1_4_pen_"+str(solar_penetration)+".csv") # Reading file
    my_data = A.loc[(A['timestamp'] >= start_date) & (A['timestamp'] < end_date)]
    my_data.reset_index(inplace=True, drop=True)
    nans_dict, nans_dict_percentage = {}, {}
    for input_variable in metrics:
        nans_dict[input_variable] = (my_data[input_variable].apply(np.isnan)).tolist() # getting a list with index positions of NaNs
        nans_dict_percentage[input_variable] = (sum(nans_dict[input_variable])/len(nans_dict[input_variable]))*100 #counting the percentage of NaNs in data
    #print(nans_dict)
    #print(nans_dict_percentage)

    #Injecting updated input variables
    for input_variable in metrics:
        temp_column = []
        if(len(updated_metric[input_variable])>0):
            for item in updated_metric[input_variable]: temp_column.append(item[3])
            # print("Temperature was increased ", temperature_column[0])
            my_data[input_variable] = temp_column
    
    my_data = my_data.interpolate(method="linear", axis=0, limit_direction='both') # linear interpolation column by column; both directions so that the first and last columns are not left alone
    #my_data = A
    timeline = my_data['timestamp'].to_list() # capturing the timeline called
    timeline_original = timeline

    # Capturing the original input variable values
    input_variable_original = {}
    for input_variable in metrics:
        input_variable_original[input_variable] = my_data[input_variable].to_list()


    #temperature_original = [99999 if math.isnan(item) else item for item in temperature_original]
    timeline = timeline[96:] # removing the first 48 entries(i.e., 12 hours)
    #print(my_data.columns)
    my_data=my_data.drop(['Unnamed: 0', 'timestamp', 'predicted mean', 'predicted std',], axis=1) # Drop this axis
    #my_data=my_data.fillna(99999)

    sequence_length = 24*4*1 #This is one day historical data #24*2 # Length of historical datapoints to use for forecast
    sequence_input = []
    for seq in gen_seq1(my_data, sequence_length, my_data.columns):
        sequence_input.append(seq)    
    sequence_input = np.asarray(sequence_input) 
    #print(sequence_input)
    
    y_ground=[]
    for i in range(len(sequence_input)):
        y_ground.append(my_data.iloc[i+96]['measurement'])   # Original code
        #y_ground.append(my_data.iloc[i]['power'])   
    y_ground=np.asarray(y_ground)
    #pd.DataFrame(y_ground).to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_ground.csv", header=None, index=None)


    y_prev = []
    sequence_target = []
    #AA=A
    B=my_data.drop(metrics, axis=1)
    for seq in gen_seq1(B, sequence_length, B.columns):
        y_prev.append(seq)
    y_prev=np.asarray(y_prev)
    y_prev=y_prev.reshape((y_prev.shape[0],y_prev.shape[1]))
    elapsed_time_prepare_input = time.process_time() - t
    #return sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original
    return sequence_input, y_ground, y_prev, input_variable_original,  nans_dict, nans_dict_percentage, elapsed_time_prepare_input, timeline, timeline_original


def autoencoder_func_1_4(sequence_input, solar_penetration):
    t = time.process_time()
    scaler_target = Scaler1D().fit(sequence_input)
    seq_inp_norm = scaler_target.transform(sequence_input) # Error maybe because of zero values in the data
    #pred_train=autoencoder_model.predict(seq_inp_norm) # this one does not work
    encoder_model = encoder_models_1_4[str(solar_penetration)]
    pred_train=encoder_model.predict(seq_inp_norm)
    #print(pred_train)
    #pd.DataFrame(pred_train).to_csv(path_parent+'/data/outputs/pen_"+str(solar_penetration)+"/pred_train.csv', header=None, index=None)
    elapsed_time_autoencoder = time.process_time() - t
    return pred_train, elapsed_time_autoencoder

def kPF_func_1_4(pred_train, solar_penetration):
    t = time.process_time()
    latent_gen = latent_gens_1_4[str(solar_penetration)]
    elapsed_time_kpf = time.process_time() - t
    return latent_gen, elapsed_time_kpf

def lstm_func_1_4(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration):
    t = time.process_time()
    aa = (latent_gen)
    enc = 20
    sequence_length = 24*4*1
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in range(total_train):
        yyy[index,0:enc]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:20],:],axis=0)
        yyy[index,enc:2*enc]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:20],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,sequence_length-1].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    T1=total_train_data[:,0:2*enc]
    T2=total_train_data[:,2*enc:2*enc+2]
    T2=T2*1e-6
    T3=np.concatenate((T1,T2),axis=1)
    total_norm_train=T3
    # scaler_target = Scaler1D().fit(total_train_data)
    # total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:2*enc+1].reshape((total_norm_train.shape[0],2*enc+1))
    Y=total_norm_train[:,2*enc+1]

    lstm_model = lstm_models_1_4[str(solar_penetration)]
    y_pred = lstm_model.predict(X)*1e6
    Y_test=Y*1e6

    mu_model = mu_models_1_4[str(solar_penetration)]
    mean_n_sd = mu_model.predict(X)*1e6
    mean_full = mean_n_sd[:,0]
    sd_full = mean_n_sd[:,1]

    conf_array_higher_limit, conf_array_lower_limit = [], []
    for index, the_data in enumerate(mean_full):
        lower_limit = mean_full[index] - 2*sd_full[index]
        upper_limit = mean_full[index] + 2*sd_full[index]
        conf_array_lower_limit.append(lower_limit) 
        conf_array_higher_limit.append(upper_limit)
    lower_y_pred = np.array(conf_array_lower_limit)
    higher_y_pred = np.array(conf_array_higher_limit)

    # print(Y_test[0], y_pred[0], mean_full[0], sd_full[0], lower_y_pred[0], higher_y_pred[0] )
    # print(Y_test[1], y_pred[1], mean_full[1], sd_full[1], lower_y_pred[1], higher_y_pred[1] )
    # print(Y_test[2], y_pred[2], mean_full[2], sd_full[2], lower_y_pred[2], higher_y_pred[2] )  
    #print(sd_full)

    
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = mean_absolute_error(Y_test, y_pred)
    mape = mean_absolute_percentage_error(Y_test, y_pred)*100
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    ape_array = calculate_ape(Y_test[np.where(Y_test!=0)],y_pred[np.where(Y_test!=0)])
    mean_ape = statistics.mean(ape_array)
    median_ape = statistics.median(ape_array)
    mode_ape = statistics.mode(ape_array)
    mse = mean_squared_error(Y_test, y_pred)
    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, mean_ape, median_ape, mode_ape,  elapsed_time_lstm


def prepare_output_df_1_4(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, input_variable_original, nans_dict, nans_dict_percentage, metrics):
    net_load = ((Y_test.flatten()).tolist())
    net_load.extend((y_pred.flatten()).tolist())
    net_load.extend((lower_y_pred.flatten()).tolist())
    net_load.extend((higher_y_pred.flatten()).tolist())
    y_pred_old = y_pred -1
    net_load.extend((y_pred_old.flatten()).tolist())

    net_load_type = (["actual"] * Y_test.size)
    net_load_type.extend(["predicted"] * y_pred.size)
    net_load_type.extend(["lower"] * lower_y_pred.size)
    net_load_type.extend(["higher"] * higher_y_pred.size)
    net_load_type.extend(["predicted_old"] * y_pred_old.size)

    years = (list(range(1,Y_test.size+1)))
    years.extend(list(range(1,y_pred.size+1)))
    years.extend(list(range(1,lower_y_pred.size+1)))
    years.extend(list(range(1,higher_y_pred.size+1)))
    years.extend(list(range(1,y_pred_old.size+1)))
    
    conf_95_df = pd.DataFrame({"timeline": timeline, "lower_limit": (lower_y_pred.flatten()).tolist(), "higher_limit": (higher_y_pred.flatten()).tolist()})
    # temperature_df = pd.DataFrame({"temperature": temperature, "timeline": timeline, "dummy":[1]*len(temperature)})
    
    input_variable_df, input_variable_df_safe ={}, {}
    for input_variable in metrics:
        input_variable_df[input_variable] = pd.DataFrame({input_variable: input_variable_original[input_variable], "timeline": timeline_original, "wasNan": nans_dict[input_variable], "dummy":[1]*len(input_variable_original[input_variable])})
        input_variable_df_safe[input_variable] = (input_variable_df[input_variable]).to_dict(orient="records")

    #print(timeline[0], timeline[-1], len(timeline))
    timeline_initial = list(timeline)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    #print(len(net_load), len(net_load_type), len(years), len(timeline))
    net_load_df = pd.DataFrame({"net_load": net_load, "net_load_type": net_load_type, "years": years, "timeline": timeline})
    # net_load_df.to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/net_load_df.csv", index=False)
    net_load_df_safe = net_load_df.to_dict(orient="records")
    conf_95_df_safe = conf_95_df.to_dict(orient="records")
    return net_load_df_safe, input_variable_df_safe, conf_95_df_safe

def validate_start_date_1_4(start_date):
    """
    This function reduces 12 hrs from the start date
    Input:
    start_date: String (e.g.: "2020-05-01 00:00:00")
    Output:
    edited_start_date: String (e.g.: "2020-04-30 12:00:00")
    """
    received_start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    edited_start_date = datetime.strftime((received_start_date - timedelta(hours = 24)), "%Y-%m-%d %H:%M:%S" )
    # Handle sending lesser than 1st Jan dates
    return edited_start_date


# Used only for Sensitivity Analysis experiments
def lstm_func_1_2x1(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration,y_pred_ground_truth):
    t = time.process_time()
    aa = (latent_gen)
    #total_train=int(len(sequence_input) - 48) # did not use this since we are not using training data
    total_train=int(len(sequence_input))
    yyy=np.zeros((total_train,40))
    for index in tqdm(range(total_train)):
        yyy[index,0:20]=np.mean(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        yyy[index,20:40]=np.std(aa[np.argsort(np.linalg.norm(aa[:,:]-pred_train[index,:],axis=1))[0:10],:],axis=0)
        
    yyy1=np.concatenate((yyy,y_prev[:,47].reshape((len(y_prev),1))),axis=1)

    y_train_sol=y_ground
    total_train_data=np.concatenate((yyy1,y_train_sol.reshape((len(y_train_sol),1))),axis=1)
    scaler_target = Scaler1D().fit(total_train_data)
    total_norm_train = scaler_target.transform(total_train_data)
    X=total_norm_train[:,0:41].reshape((total_norm_train.shape[0],41,1))
    Y=total_norm_train[:,41]

    lstm_model = lstm_models[str(solar_penetration)]
    y_pred = lstm_model.predict(X)
    y_pred=y_pred*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    Y_test=Y*(np.max(total_train_data[:,41])-np.min(total_train_data[:,41]))+np.min(total_train_data[:,41])
    #y_pred = y_pred.flatten()
    #print(y_pred, Y_test)
    mean = lambda x: x.mean()#.flatten()
    sd = lambda x: x.std()#.flatten() 
    conf_int_95 = np.array([mean(y_pred) - 2*sd(y_pred), mean(y_pred) + 2*sd(y_pred)]) #https://datascience.stackexchange.com/questions/109048/get-the-confidence-interval-for-prediction-results-with-lstm
    two_sd = 2*sd(y_pred)
    # lower_y_pred = y_pred + conf_int_95[0]
    # higher_y_pred = y_pred + conf_int_95[1]
    lower_y_pred = y_pred - two_sd
    higher_y_pred = y_pred + two_sd
    print("Conf", conf_int_95)
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/y_pred.csv", y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/Y_test.csv", Y_test, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/lower_y_pred.csv", lower_y_pred, delimiter=",")
    #np.savetxt(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/higher_y_pred.csv", higher_y_pred, delimiter=",")
    mae = mean_absolute_error(y_pred_ground_truth, y_pred)
    mape = mean_absolute_percentage_error(y_pred_ground_truth, y_pred)
    # crps = ps.crps_ensemble(y_pred.flatten(), Y_test).mean()
    # pbb = pbb_calculation(Y_test, y_pred.flatten())
    mse = mean_squared_error(Y_test, y_pred)
    elapsed_time_lstm = time.process_time() - t
    #return y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm
    return y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm

def generate_comparison_image(y_pred, Y_test, solar_penetration, purpose, start_date, end_date):
    """
    This function generates an image(through matplotlib) comparing 
    the actual and predicted net load values through line charts

    Inputs:
    y_pred: the predicted net load
    Y_test: the actual net load

    Output:
    Image: saved in the folder /data/outputs/comparison.png 
    (path is relative to the project folder)
    """
    safe_file_name = start_date.replace(" ", "T").replace(":","")+"_to_"+end_date.replace(" ", "T").replace(":","")
    global plt
    plt.switch_backend('agg') # Saves from the error "main not in main"
    plt.rcParams["figure.figsize"] = (20,10)
    plt.rcParams.update({'font.size': 18})
    plt.plot(Y_test, label="actual")
    if(purpose == "processor"): y_pred = y_pred.flatten()
    plt.plot(y_pred, label="prediction")
    plt.legend(loc="upper right")
    plt.title("Comparison of Net Load Actual vs. Prediction at Solar Penetration="+str(solar_penetration)+"%")
    plt.xlabel("Time Intervals from %s to %s" %(start_date, end_date))
    plt.ylabel("Net Load (kW)")
    plt.savefig(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/comparison_"+safe_file_name+".png", facecolor='w')
    plt.rcParams["figure.figsize"] = plt.rcParamsDefault["figure.figsize"]
    plt.clf()
    return 1

def validate_start_date(start_date):
    """
    This function reduces 24 hrs from the start date
    Input:
    start_date: String (e.g.: "2020-05-02 00:00:00")
    Output:
    edited_start_date: String (e.g.: "2020-05-01 12:00:00")
    """
    received_start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    edited_start_date = datetime.strftime((received_start_date - timedelta(hours = 12)), "%Y-%m-%d %H:%M:%S" )
    # Handle sending lesser than 1st Jan dates
    return edited_start_date

def prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans, humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans):
    net_load = ((Y_test.flatten()).tolist())
    net_load.extend((y_pred.flatten()).tolist())
    net_load.extend((lower_y_pred.flatten()).tolist())
    net_load.extend((higher_y_pred.flatten()).tolist())
    y_pred_old = y_pred -1
    net_load.extend((y_pred_old.flatten()).tolist())

    net_load_type = (["actual"] * Y_test.size)
    net_load_type.extend(["predicted"] * y_pred.size)
    net_load_type.extend(["lower"] * lower_y_pred.size)
    net_load_type.extend(["higher"] * higher_y_pred.size)
    net_load_type.extend(["predicted_old"] * y_pred_old.size)

    years = (list(range(1,Y_test.size+1)))
    years.extend(list(range(1,y_pred.size+1)))
    years.extend(list(range(1,lower_y_pred.size+1)))
    years.extend(list(range(1,higher_y_pred.size+1)))
    years.extend(list(range(1,y_pred_old.size+1)))
    
    conf_95_df = pd.DataFrame({"timeline": timeline, "lower_limit": (lower_y_pred.flatten()).tolist(), "higher_limit": (higher_y_pred.flatten()).tolist()})
    # temperature_df = pd.DataFrame({"temperature": temperature, "timeline": timeline, "dummy":[1]*len(temperature)})
    temperature_df = pd.DataFrame({"temperature": temperature_original, "timeline": timeline_original, "wasNan": temperature_nans, "dummy":[1]*len(temperature_original)})
    humidity_df = pd.DataFrame({"humidity": humidity_original, "timeline": timeline_original, "wasNan": humidity_nans, "dummy":[1]*len(humidity_original)})
    apparent_power_df = pd.DataFrame({"apparent_power": apparent_power_original, "timeline": timeline_original, "wasNan": apparent_power_nans, "dummy":[1]*len(apparent_power_original)})
    #print(timeline[0], timeline[-1], len(timeline))
    timeline_initial = list(timeline)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    #print(len(net_load), len(net_load_type), len(years), len(timeline))
    net_load_df = pd.DataFrame({"net_load": net_load, "net_load_type": net_load_type, "years": years, "timeline": timeline})
    # net_load_df.to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/net_load_df.csv", index=False)
    net_load_df_safe = net_load_df.to_dict(orient="records")
    conf_95_df_safe = conf_95_df.to_dict(orient="records")
    temperature_df_safe = temperature_df.to_dict(orient="records")
    humidity_df_safe = humidity_df.to_dict(orient="records")
    apparent_power_df_safe = apparent_power_df.to_dict(orient="records")
    return net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe

def prepare_output_df(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans, humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans):
    # net_load = ((Y_test.flatten()).tolist())
    # net_load.extend((y_pred.flatten()).tolist())
    # net_load.extend((lower_y_pred.flatten()).tolist())
    # net_load.extend((higher_y_pred.flatten()).tolist())
    # y_pred_old = y_pred -1
    # net_load.extend((y_pred_old.flatten()).tolist())

    # net_load_type = (["actual"] * Y_test.size)
    # net_load_type.extend(["predicted"] * y_pred.size)
    # net_load_type.extend(["lower"] * lower_y_pred.size)
    # net_load_type.extend(["higher"] * higher_y_pred.size)
    # net_load_type.extend(["predicted_old"] * y_pred_old.size)

    mae = mean_absolute_error(Y_test, y_pred)
    mape = mean_absolute_percentage_error(Y_test, y_pred)

    print(len(y_pred), len(Y_test), len(lower_y_pred), len(higher_y_pred), len(timeline), len(timeline_original))

    net_load = []
    net_load.extend(Y_test)
    net_load.extend(y_pred)
    net_load.extend(lower_y_pred)
    net_load.extend(higher_y_pred)
    #y_pred_old = y_pred -1 # problematic line
    y_pred_old =  [x - 1 for x in y_pred]
    net_load.extend(y_pred_old)

    net_load_type = (["actual"] * len(Y_test))
    net_load_type.extend(["predicted"] * len(y_pred))
    net_load_type.extend(["lower"] * len(lower_y_pred))
    net_load_type.extend(["higher"] * len(higher_y_pred))
    net_load_type.extend(["predicted_old"] * len(y_pred_old))

    years = (list(range(1,len(Y_test)+1)))
    years.extend(list(range(1,len(y_pred)+1)))
    years.extend(list(range(1,len(lower_y_pred)+1)))
    years.extend(list(range(1,len(higher_y_pred)+1)))
    years.extend(list(range(1,len(y_pred_old)+1)))

    print(timeline[0], timeline[-1], len(timeline), len(lower_y_pred), len(higher_y_pred), len(temperature_original), len(timeline_original))
    
    #conf_95_df = pd.DataFrame({"timeline": timeline, "lower_limit": (lower_y_pred.flatten()).tolist(), "higher_limit": (higher_y_pred.flatten()).tolist()})
    conf_95_df = pd.DataFrame({"timeline": timeline, "lower_limit": lower_y_pred, "higher_limit": higher_y_pred})
    #conf_95_df = pd.DataFrame({"timeline": timeline, "lower_limit": timeline, "higher_limit": timeline})
    # temperature_df = pd.DataFrame({"temperature": temperature, "timeline": timeline, "dummy":[1]*len(temperature)})
    temperature_df = pd.DataFrame({"temperature": temperature_original, "timeline": timeline_original, "wasNan": temperature_nans, "dummy":[1]*len(temperature_original)})
    humidity_df = pd.DataFrame({"humidity": humidity_original, "timeline": timeline_original, "wasNan": humidity_nans, "dummy":[1]*len(humidity_original)})
    apparent_power_df = pd.DataFrame({"apparent_power": apparent_power_original, "timeline": timeline_original, "wasNan": apparent_power_nans, "dummy":[1]*len(apparent_power_original)})
    print(timeline[0], timeline[-1], len(timeline))
    timeline_initial = list(timeline)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    timeline.extend(timeline_initial)
    print("Net load df ", len(net_load), len(net_load_type), len(years), len(timeline))
    net_load_df = pd.DataFrame({"net_load": net_load, "net_load_type": net_load_type, "years": years, "timeline": timeline})
    # net_load_df.to_csv(path_parent+"/data/outputs/pen_"+str(solar_penetration)+"/net_load_df.csv", index=False)
    net_load_df_safe = net_load_df.to_dict(orient="records")
    conf_95_df_safe = conf_95_df.to_dict(orient="records")
    temperature_df_safe = temperature_df.to_dict(orient="records")
    humidity_df_safe = humidity_df.to_dict(orient="records")
    apparent_power_df_safe = apparent_power_df.to_dict(orient="records")
    return net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe, mae, mape

def get_time_intervals(start_date, end_date):
    time_intervals = []
    received_start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    received_end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    edited_start_date = received_start_date
    edited_end_date = received_start_date + timedelta(hours = 12) # increasing time by 15
    while(edited_end_date<received_end_date):
        time_intervals.append([datetime.strftime((edited_start_date - timedelta(hours = 12)), "%Y-%m-%d %H:%M:%S"), datetime.strftime(edited_end_date, "%Y-%m-%d %H:%M:%S")])
        #time_intervals.append([datetime.strftime((edited_start_date), "%Y-%m-%d %H:%M:%S"), datetime.strftime(edited_end_date, "%Y-%m-%d %H:%M:%S")])
        edited_start_date = edited_start_date + timedelta(hours = 0.25)
        edited_end_date = edited_end_date + timedelta(hours = 0.25)
    return time_intervals

def calculate_constant_bias_absolute(arr,noise):
    noisy_arr = list(map(lambda el: el+noise, arr))
    return noisy_arr

def getRandomArbitrary(min, max):
      return random.random() * (max - min) + min

def calculate_uniform_noise(arr,noise):
    lower_number = 1-(noise/100) 
    upper_number = 1+(noise/100) 
    noisy_arr = [getRandomArbitrary(lower_number*el, upper_number*el) for el in arr]
    return noisy_arr
def calculate_uniform_noise_increase(arr,noise):
    lower_number = 1-(noise/100) 
    upper_number = 1+(noise/100) 
    noisy_arr = [getRandomArbitrary(el, upper_number*el) for el in arr]
    return noisy_arr
def calculate_uniform_noise_decrease(arr,noise):
    lower_number = 1-(noise/100) 
    upper_number = 1+(noise/100) 
    noisy_arr = [getRandomArbitrary(lower_number*el, el) for el in arr]
    return noisy_arr
def convert_to_Array_of_Arrays(input, the_metric):
    output = []
    for obj in input:
        output.append([obj["dummy"], obj["timeline"], obj["wasNan"], obj[the_metric]])
    return output

### Callable functions ###
# deprecated
@app.route('/api/v1/processor',methods = ['POST', 'GET'])
def processor_v1(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
    print(start_date)
    sequence_input, y_ground, y_prev, temperature, humidity, apparent_power, elapsed_time_prepare_input = prepare_input0(start_date, end_date, solar_penetration)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, mae, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

# deprecated
@app.route('/api/v1.1/processor',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
def processor_v1_1(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
    print(start_date, solar_penetration)
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, mae, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe = prepare_output_df0(y_pred, Y_test, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v1.2/processor',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
@app.route('/api/v@latest/processor_15min_ahead',methods = ['POST', 'GET'])
def processor(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration, updated_metric)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe = prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    print("MAE: ", mae)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v1.3/processor',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
@app.route('/api/v@latest/processor_24hr_ahead',methods = ['POST', 'GET'])
def processor3(start_date="2020-01-03 00:00:00", end_date="2020-01-04 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    #start_date = validate_start_date(start_date)
    global default_response
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        #start_date = validate_start_date(req["start_date"])
        start_date = req["start_date"]
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric] 
        
        """ Check if all initial parameters are same"""
        metrics_updated_dict = req["metrics_updated"]
        metrics_not_updated = all(value == 0 for value in metrics_updated_dict.values()) # This variable checks if none of the metrics are updated
        if(start_date == "2020-01-03 00:00:00" and end_date == "2020-01-04 00:00:00" and solar_penetration == 50 and metrics_not_updated):
            print(" I am in out loop")  
            print(default_response)  
            return default_response       
    print(start_date, solar_penetration)

    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    time_intervals = get_time_intervals(validate_start_date(start_date), end_date)
    print("time intervals ", time_intervals)
    temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original, df_updated_metric = prepare_general_input(validate_start_date(start_date),end_date, solar_penetration, updated_metric)
    print("df updated metric ", df_updated_metric)
    y_pred_mega, Y_test_mega, lower_y_pred_mega, higher_y_pred_mega = [], [], [], []
    for time_interval in time_intervals:
        sequence_input, y_ground, y_prev = prepare_input(time_interval[0], time_interval[1], solar_penetration, updated_metric, df_updated_metric)
        pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
        latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
        #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
        y_pred, Y_test, lower_y_pred, higher_y_pred, elapsed_time_lstm = lstm_func2(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
        y_pred_mega.append(y_pred[0])
        Y_test_mega.append(Y_test[0])
        lower_y_pred_mega.append(lower_y_pred[0])
        higher_y_pred_mega.append(higher_y_pred[0])
    print(y_pred_mega)
    print("Time sent to prepare general input", validate_start_date(start_date),end_date)
    print("df updated metric ", df_updated_metric)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe, mae, mape = prepare_output_df(y_pred_mega, Y_test_mega, lower_y_pred_mega, higher_y_pred_mega, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    print("MAE: ", mae)
    print("total time: ", elapsed_time_total)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v@initial/processor',methods = ['POST', 'GET'])
def processor_initial():
    global default_response
    default_response = processor3()
    return "The program is now initiated"

@app.route('/api/v1.2x0/processor',methods = ['POST', 'GET'])
def processor_v1_2x0(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        #print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    #print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration, updated_metric)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe = prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    #print("MAE: ", mae)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v1.2x1/processor',methods = ['POST', 'GET'])
def processor_v1_2x1(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    y_pred_ground_truth = []
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        #print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        y_pred_ground_truth = req["y_pred_ground_truth"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    #print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration, updated_metric)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm = lstm_func_1_2x1(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration, y_pred_ground_truth)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe = prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    #print("MAE: ", mae)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;


@app.route('/api/v1.3/sa_processor',methods = ['POST', 'GET'])
@app.route('/api/v@latest/sa_processor',methods = ['POST', 'GET'])
def sa_processor():
    input_variable_sa, start_date_sa, end_date_sa, months_sa, noise_level_sa, number_of_observations_sa, noise_direction_sa = "", 2, 4, [], 0, 0, ""
    if(request.is_json):
        req = request.get_json()
        #print("Reading JSON")
        input_variable_sa = req["input_variable_sa"]
        start_date_sa = req["start_date_sa"]
        end_date_sa = req["end_date_sa"]
        months_sa = req["months_sa"]
        noise_level_sa = req["noise_level_sa"]
        number_of_observations_sa = req["number_of_observations_sa"]
        noise_direction_sa = req["noise_direction_sa"]
        name_sa = req["name_sa"]
    print(input_variable_sa, start_date_sa, end_date_sa, months_sa, noise_level_sa, number_of_observations_sa, noise_direction_sa) 

    """Setting variables"""
    url_base = "http://localhost:5000"
    api_url = url_base + "/api/v1.2x0/processor"
    api_url2 = url_base + "/api/v1.2x1/processor"
    main_dir=os.getcwd()
    # Setting months
    start_date_list, end_date_list = [], []
    start_date_sa_copy, end_date_sa_copy = start_date_sa, end_date_sa
    for each_month in months_sa:
        month_string = list(calendar.month_name).index(each_month)
        if(month_string/10<1): month_string = "0"+str(month_string) # Adding padding to month
        else: month_string = str(month_string)
        if(start_date_sa_copy/10<1): start_date_sa = "0"+str(start_date_sa_copy)
        if(end_date_sa_copy/10<1): end_date_sa = "0"+str(end_date_sa_copy)
        edited_start_date = "2020-"+month_string+"-"+str(start_date_sa)+" 00:00:00"
        edited_end_date = "2020-"+month_string+"-"+str(end_date_sa)+" 00:00:00"
        start_date_list.append(edited_start_date)
        end_date_list.append(edited_end_date)
        start_date= edited_start_date #"2020-02-03 00:00:00" #February
        end_date=edited_end_date #"2020-02-05 00:00:00"
    print(start_date_list, end_date_list)    

    solar_penetration=50
    metrics_updated = {}
    updated_metric = {"temperature":[], "humidity":[], "apparent_power":[]}
    metrics = ["temperature", "humidity", "apparent_power"]
    for em in metrics:
        metrics_updated[em] = 0
    print("My Printing")
    print(metrics_updated, updated_metric, edited_start_date, edited_end_date)    
    print(calculate_uniform_noise_increase([1,3,5], 5))
    print(calculate_uniform_noise_decrease([1,3,5], 5))  
    noise_function = ""
    if(noise_direction_sa == "bidirectional"): noise_function = calculate_uniform_noise
    elif(noise_direction_sa == "positive_direction"): noise_function = calculate_uniform_noise_increase 
    else: noise_function = calculate_uniform_noise_decrease 
    
    mae_values, mape_values, mae_values_temp_all, mape_values_temp_all = [], [], [], []
    for month_index, month in tqdm(enumerate(months_sa)):
        start_date = start_date_list[month_index]
        end_date = end_date_list[month_index]
        """Initial Call"""
        payload = {"start_date": start_date, "end_date": end_date, "solar_penetration": solar_penetration, "metrics_updated":metrics_updated, "updated_metric":updated_metric}
        headers =  {"Content-Type":"application/json"}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        initial_output = response.json()
        y_pred_ground_truth = initial_output["predicted_net_load"]
        metric_variable_df = initial_output[input_variable_sa+"_df"]
        formatted_array = convert_to_Array_of_Arrays(metric_variable_df, input_variable_sa)

        """Main call"""
       
        for el in tqdm(np.arange(0.0, noise_level_sa+1, 1)):
            mae_values_temp, mape_values_temp = [], []
            for em in range(0,number_of_observations_sa):
            #print("Started for ", el)
                formatted_array_mini = [x[3] for x in formatted_array]
                updated_metric_variable = noise_function(formatted_array_mini, el)
                #print(formatted_array_mini[0], updated_temperature[0])
                updated_metric_variable2=[]
                for i in range(0,len(formatted_array)): updated_metric_variable2.append([formatted_array[i][0], formatted_array[i][1], formatted_array[i][2], updated_metric_variable[i]])
                #print(updated_temperature2[0])
                updated_metric[input_variable_sa] = updated_metric_variable2
                metrics_updated[input_variable_sa] = 1
                #print(updated_metric["temperature"][0], metrics_updated["temperature"])
                payload = {"start_date": start_date, "end_date": end_date, "solar_penetration": solar_penetration, "metrics_updated":metrics_updated, "updated_metric":updated_metric, "y_pred_ground_truth": y_pred_ground_truth}
                headers =  {"Content-Type":"application/json"}
                response = requests.post(api_url2, data=json.dumps(payload), headers=headers)
                res = response.json()
                mae_values_temp.append(res["7. MAE"])
                mape_values_temp.append(res["8. MAPE"])
                mae_values_temp_all.append([el, res["7. MAE"], month])
                mape_values_temp_all.append([el, res["8. MAPE"], month])
                print("Month: "+str(month)+" Noise Level: "+str(el)+" Observation: "+str(em))
            #mae_values.append([el, res["7. MAE"]])
            #mape_values.append([el, res["8. MAPE"]])
            mae_values.append([el, np.mean(mae_values_temp), month])
            mape_values.append([el, np.mean(mape_values_temp), month])
            print("Ended for ", el)
    
    """
    Saving the results
    """
    df_mae = pd.DataFrame(mae_values, columns=["Noise_Percentage", "Mean_MAE", "Month"])
    df_mae_grouped = df_mae.groupby(["Noise_Percentage"]).mean().reset_index()
    df_mae_grouped["Month"] = "Average"
    df_mae = pd.concat([df_mae, df_mae_grouped])
    print(main_dir)
    job_path = main_dir+"/pyAPI/outputs/jobs/"+name_sa
    if not os.path.exists(job_path):
        os.makedirs(job_path)
    df_mae.to_csv(main_dir+"/pyAPI/outputs/jobs/"+name_sa+"/mae.csv", sep=',',index=False)
    df_mae_all = pd.DataFrame(mae_values_temp_all, columns=["Noise_Percentage", "MAE", "Month"])
    df_mae_all.to_csv(main_dir+"/pyAPI/outputs/jobs/"+name_sa+"/mae_all.csv", sep=',',index=False)

    df_mape = pd.DataFrame(mape_values, columns=["Noise_Percentage", "Mean_MAPE", "Month"])
    df_mape_grouped = df_mape.groupby(["Noise_Percentage"]).mean().reset_index()
    df_mape_grouped["Month"] = "Average"
    df_mape = pd.concat([df_mape, df_mape_grouped])
    df_mape.to_csv(main_dir+"/pyAPI/outputs/jobs/"+name_sa+"/mape.csv", sep=',',index=False)
    df_mape_all = pd.DataFrame(mape_values_temp_all, columns=["Noise_Percentage", "MAPE", "Month"])
    df_mape_all.to_csv(main_dir+"/pyAPI/outputs/jobs/"+name_sa+"/mape_all.csv", sep=',',index=False)

    """
    Creating title
    """
    title_month_string = ", ".join(months_sa)
    the_title = "Sensitivity analysis by adding uniform noise(direction: "+noise_direction_sa+") in "+input_variable_sa+" ("+title_month_string+")"
    with open(main_dir+"/pyAPI/outputs/jobs/"+name_sa+"/title.txt", 'w') as f:
        f.write(the_title)
    
    """
    Output
    """
    # plt.rcParams["figure.figsize"] = (30,10)
    # plt.rcParams.update({'font.size': 18})
    # xpoints = [x[0] for x in mae_values]
    # ypoints = [x[1] for x in mae_values]
    # plt.plot(xpoints, ypoints, label="MAE")
    # xpoints_scatter = [x[0] for x in mae_values_temp_all]
    # ypoints_scatter = [x[1] for x in mae_values_temp_all]
    # plt.scatter(xpoints_scatter, ypoints_scatter, alpha=0.3)
    # #plt.plot(y_pred, label="pred")
    # plt.legend(loc="upper right")
    # plt.title("Sensitivity analysis by adding uniform noise (direction:"+noise_direction_sa+") in "+input_variable_sa+" (February)")
    # #plt.xlabel("Temperature bias (°F)")
    # plt.xlabel("Noise(%)")
    # plt.ylabel("MAE (kW)")
    # plt.savefig(main_dir+"/src/outputs/sensitivity_analysis/temperature/uniform_noise/february/mae_positive.png", facecolor='w')
    # plt.rcParams["figure.figsize"] = plt.rcParamsDefault["figure.figsize"]

    final_result = {"message": "This endpoint is not ready yet"}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v1.2x0_shap1/processor',methods = ['POST', 'GET'])
def processor_v1_2x0_shap1(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        #print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    #print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration, updated_metric)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, elapsed_time_lstm = lstm_func_shap1(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe = prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    #print("MAE: ", mae)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;


@app.route('/api/v1/stability_check', methods = ['POST', 'GET'])
def stability_check():
    """
    This function checks for the stability of the program.
    Calls to the random functions make it difficult to produce reproducible results.
    This function specifically runs multiple times to check if outputs are same with same input

    Input:(optional)
    n: the number of times to execute the program
    If supplying different value of n, use the following query:
    /api/v1/stability_check?n=5

    Output:
    JSON output with the stability result, n, and average execution time
    """
    time_array, mae_array, mape_array, crps_array, pbb_array, answer, errors = [], [], [], [], [], "", ["None"]
    n = request.args.get('n') 
    try:
        n = int(n)
        if(n>500): raise Exception("High value of n")
    except Exception as e:
        n = 3
        if(str(e) == "High value of n"): errors.append("Too high value for n, hence using the default value of 3")
        else: errors.append("Incorrect value for n, hence using the default value of 3")   
    pen = request.args.get('pen', default =50, type = int)
    if(str(pen) not in solar_penetration_levels):
        pen =50 # handling errorneous inputs
        errors.append("Incorrect solar penetration level sent, hence using the default level 50%")
    start_date="2020-05-01 00:00:00"
    end_date="2020-05-03 00:00:00"
    for i in range(n):
        print("Stability Check Round %d" %i)
        output = processor(start_date, end_date, pen)
        output = output.get_json()
        time_array.append(output["6. total time taken"])
        mae_array.append(output["7. MAE"])
        # mape_array.append(output["8. MAPE"])
        # crps_array.append(output["9. CRPS"])
        # pbb_array.append(output["10. PBB"])
    #if((len(set(mae_array)) == 1) & (len(set(mape_array)) == 1) & (len(set(crps_array)) == 1) & (len(set(pbb_array)) == 1)): answer = "Program is stable"
    if((len(set(mae_array)) == 1)): answer = "Program is stable"
    else: answer = "Program is NOT stable"
    if(len(errors)>1): errors.pop(0) # Removing "None" if there are errors
    error_message = "; ".join(errors) 
    #message={"1. message": answer, "2. Number of times executed": n, "3. Average execution time (seconds)": sum(time_array)/len(time_array), "4. MAE": mae_array[0], "5. MAPE": mape_array[0], "6. CRPS": crps_array[0], "7. PBB": pbb_array[0]}
    message={"1. message": answer, "2. Number of times executed": n, "3. Solar penetration level (%)": pen, "4. Average execution time (seconds)": sum(time_array)/len(time_array), "5. MAE": mae_array[0], "6. Errors": error_message}
    app.logger.info(message)
    return message

@app.route("/api/v1/metrics_check", methods = ['POST', 'GET'])
def metrics_check():
    global solar_penetration_levels
    summer_48_hrs = ["2020-05-01 00:00:00", "2020-05-03 00:00:00"]
    winter_48_hrs = ["2020-12-01 00:00:00", "2020-12-03 00:00:00"]
    dates = [summer_48_hrs, winter_48_hrs]
    solar_penetration_array, start_date_array, end_date_array, season_array, time_taken_array, mae_array, mape_array, crps_array, pbb_array = [], [], [], [], [], [], [], [], []
    for solar_penetration in solar_penetration_levels:
        for date in dates:
            start_date, end_date = date[0], date[1]
            resp = processor(start_date, end_date, solar_penetration)
            processor_result = resp.get_json()
            y_pred = processor_result["predicted_net_load"]
            Y_test = processor_result["actual_net_load"]
            mae_array.append(processor_result["7. MAE"])
            mape_array.append(mean_absolute_percentage_error(Y_test, y_pred))
            crps_array.append(ps.crps_ensemble(y_pred, Y_test).mean())
            pbb_array.append(pbb_calculation(Y_test, y_pred))
            time_taken_array.append(processor_result["6. total time taken"])
            solar_penetration_array.append(solar_penetration)
            start_date_array.append(start_date)
            end_date_array.append(end_date)
            season = "Summer" if(dates.index(date) == 0) else "Winter"
            season_array.append(season)
            generate_comparison_image(y_pred, Y_test, solar_penetration, "metrics_check", start_date, end_date)
    d = {"Solar_Penetration": solar_penetration_array, "Start_date": start_date_array, "End_date": end_date_array,
            "Season": season_array, "Time_taken": time_taken_array, "MAE": mae_array, "MAPE": mape_array}#, "CRPS": crps_array, "PBB":pbb_array}   
    df = pd.DataFrame(d)
    df.to_csv(path_parent+"/metrics.csv", index=False)             
    return "Output saved at metrics.csv"

@app.route('/outputs/jobs/<path:path>')
def send_report(path):
    """Returns the file at the specified path"""
    print(path)
    return send_from_directory('outputs/jobs', path)
@app.route('/check_job/jobs/<path:path>', methods = ['POST', 'GET'])
def check_if_job_exists(path):
    """Returns if a specified folder is present or not"""
    print(path)
    main_dir=os.getcwd()
    path_to_check = main_dir+"/pyAPI/outputs/jobs/"+path
    present = os.path.isdir(path_to_check)
    final_result = {"message": present}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response; 

@app.route('/check_job/all_jobs', methods = ['POST', 'GET'])
def return_job_list():
    """Returns all jobs"""
    main_dir=os.getcwd()
    path_to_check = main_dir+"/pyAPI/outputs/jobs/"
    all_jobs = os.listdir(path_to_check)
    final_result = {"message": all_jobs}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response; 

### New Processor functions ###
@app.route('/api/v@1.3/processor',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
def processor_1_3(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=50):
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date(start_date)
    updated_metric = {}
    metrics = ["temperature", "humidity", "apparent_power"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, temperature, temperature_original, temperature_nans, temperature_nans_percentage, humidity, humidity_original, humidity_nans, humidity_nans_percentage, apparent_power, apparent_power_original, apparent_power_nans, apparent_power_nans_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input0(start_date, end_date, solar_penetration, updated_metric)
    pred_train, elapsed_time_autoencoder = autoencoder_func(sequence_input, solar_penetration)
    latent_gen, elapsed_time_kpf = kPF_func(pred_train, solar_penetration)
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, mean_ape, median_ape, mode_ape, elapsed_time_lstm = lstm_func_1_3(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    net_load_df_safe, temperature_df_safe, humidity_df_safe, apparent_power_df_safe, conf_95_df_safe = prepare_output_df0(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, temperature_original, temperature_nans,  humidity, humidity_original, humidity_nans, apparent_power, apparent_power_original, apparent_power_nans)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    print("MAE: ", mae)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape,"8a. Mean APE": mean_ape, "8b. Median APE": median_ape,  "8c. Mode APE": mode_ape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(), "temperature":temperature, "humidity":humidity, "apparent_power":apparent_power, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe, "temperature_df": temperature_df_safe, "temperature_nans_percentage":temperature_nans_percentage, "humidity_df": humidity_df_safe, "humidity_nans_percentage": humidity_nans_percentage, "apparent_power_df": apparent_power_df_safe, "apparent_power_nans_percentage": apparent_power_nans_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;


@app.route('/api/v@1.4/processor',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
def processor_1_4(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=20):
    """
    This function processes the inputs from the API caller (generally front-end), passes them through different functions,
    and then returns the output to the API caller.
    Inputs:
    start_date: starting date for the prediction (String)
    end_date: ending date for the prediction (String)
    solar_penetration: solar penetration level (Integer)
    metrics_updated: array containing the signals if a certain metric is updated; if updated, then 1 else -1
    updated_metric: dict containing the updated values of the metrics

    Output:
    JSON message including different outputs
    """
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date_1_4(start_date)
    updated_metric = {}
    #metrics = ["temperature", "humidity", "apparent_power"]
    metrics = ["SZA", "AZM", "ETR", "GHI", "Wind_Speed", "Temperature"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date_1_4(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        # Need to enable this in order to enable updates
        print(req["metrics_updated"])
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, input_variable_original, nans_dict, nans_dict_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input_1_4(start_date, end_date, solar_penetration, updated_metric, metrics)
    print("Prepare input PASSED")
    pred_train, elapsed_time_autoencoder = autoencoder_func_1_4(sequence_input, solar_penetration)
    print("Autoencoder PASSED")
    latent_gen, elapsed_time_kpf = kPF_func_1_4(pred_train, solar_penetration)
    print("kPF PASSED")
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, mean_ape, median_ape, mode_ape, elapsed_time_lstm = lstm_func_1_4(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    print("LSTM PASSED")
    net_load_df_safe, input_variable_df_safe, conf_95_df_safe = prepare_output_df_1_4(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, input_variable_original, nans_dict, nans_dict_percentage, metrics)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    print("MAPE: ", mape)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "8a. Mean APE": mean_ape, "8b. Median APE": median_ape,  "8c. Mode APE": mode_ape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(),  "input_variable_df":input_variable_df_safe, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe,  "nans_dict_percentage": nans_dict_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;

@app.route('/api/v@1.4/processor2',methods = ['POST', 'GET'])
#@app.route('/api/v@latest/processor',methods = ['POST', 'GET'])
def processor_1_4_2(start_date="2020-05-01 00:00:00", end_date="2020-05-03 00:00:00", solar_penetration=20):
    """
    This function processes the inputs from the API caller (generally front-end), passes them through different functions,
    and then returns the output to the API caller.
    Inputs:
    start_date: starting date for the prediction (String)
    end_date: ending date for the prediction (String)
    solar_penetration: solar penetration level (Integer)
    metrics_updated: array containing the signals if a certain metric is updated; if updated, then 1 else -1
    updated_metric: dict containing the updated values of the metrics

    Output:
    JSON message including different outputs
    """
    t = time.process_time()
    #start_date, end_date, solar_penetration = "2020-05-01 00:00:00", "2020-05-03 00:00:00", 50
    start_date = validate_start_date_1_4(start_date)
    updated_metric = {}
    #metrics = ["temperature", "humidity", "apparent_power"]
    metrics = ["SZA", "AZM", "ETR", "GHI", "Wind_Speed", "Temperature"]
    for i in metrics: updated_metric[i] = []
    if(request.is_json):
        req = request.get_json()
        print("Reading JSON")
        start_date = validate_start_date_1_4(req["start_date"])
        end_date = req["end_date"]
        solar_penetration = req["solar_penetration"]
        # Need to enable this in order to enable updates
        print(req["metrics_updated"])
        for metric in metrics:
            if(req["metrics_updated"][metric] == 1): updated_metric[metric] = req["updated_metric"][metric]        
    print(start_date, solar_penetration)
    # if(len(updated_metric["temperature"])>0): print((updated_metric["temperature"])[0])
    sequence_input, y_ground, y_prev, input_variable_original, nans_dict, nans_dict_percentage, elapsed_time_prepare_input, timeline, timeline_original = prepare_input_1_4(start_date, end_date, solar_penetration, updated_metric, metrics)
    print("Prepare input PASSED")
    pred_train, elapsed_time_autoencoder = autoencoder_func_1_4(sequence_input, solar_penetration)
    print("Autoencoder PASSED")
    latent_gen, elapsed_time_kpf = kPF_func_1_4(pred_train, solar_penetration)
    print("kPF PASSED")
    #y_pred, Y_test, mae, mape, crps, pbb, mse, elapsed_time_lstm = lstm_func(latent_gen, sequence_input, pred_train, y_ground, y_prev)
    y_pred, Y_test, lower_y_pred, higher_y_pred, mae, mape, mean_ape, median_ape, mode_ape, elapsed_time_lstm = lstm_func_1_4(latent_gen, sequence_input, pred_train, y_ground, y_prev, solar_penetration)
    print("LSTM PASSED")
    net_load_df_safe, input_variable_df_safe, conf_95_df_safe = prepare_output_df_1_4(y_pred, Y_test, lower_y_pred, higher_y_pred, timeline, timeline_original, input_variable_original, nans_dict, nans_dict_percentage, metrics)
    #generate_comparison_image(y_pred, Y_test, solar_penetration, "processor", start_date, end_date)
    elapsed_time_total = time.process_time() - t
    print("MAPE: ", mape)
    #final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "9. CRPS": crps, "10. PBB": pbb, "11. MSE": mse}
    final_result ={"1. message":"Program executed", "2. time taken (prepare input)": elapsed_time_prepare_input, "3. time taken (autoencoder)":elapsed_time_autoencoder, "4. time taken (kPF)": elapsed_time_kpf, "5. time taken (LSTM)": elapsed_time_lstm, "6. total time taken":elapsed_time_total, "7. MAE": mae, "8. MAPE": mape, "8a. Mean APE": mean_ape, "8b. Median APE": median_ape,  "8c. Mode APE": mode_ape, "predicted_net_load":y_pred.flatten().tolist(), "actual_net_load": Y_test.tolist(), "predicted_net_load_conf_95_higher":higher_y_pred.flatten().tolist(), "predicted_net_load_conf_95_lower":lower_y_pred.flatten().tolist(),  "input_variable_df":input_variable_df_safe, "net_load_df": net_load_df_safe, "conf_95_df":conf_95_df_safe,  "nans_dict_percentage": nans_dict_percentage}
    response=make_response(jsonify(final_result), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;




@app.errorhandler(404)
def handle_404(e):
    # handle all other routes here
    return 'No such API endpoint available.'

@app.route('/',methods = ['POST', 'GET'])
def index():
    final_result2 ={"message": "This is not an error. This endpoint is not configured for public use."}
    
    response=make_response(jsonify(final_result2), 200) #removed processing
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response;