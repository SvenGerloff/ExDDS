import numpy as np
import pandas as pd
import pre_processing_functions
from numpy.random import seed
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import GRU
from tensorflow.keras.layers import Masking
from tensorflow.keras.layers import TimeDistributed
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.models import load_model


''' Sessions. '''
data_sessions = pd.read_csv('sessions_train.csv')

data_sessions = pre_processing_functions.one_hot_encode_actions_fit_transform(data_sessions)[0]

# Add column with start time for each session.
data_sessions['session_start'] = data_sessions.groupby(['event_id', 'session_id']).action_time.transform(np.min)
data_sessions = data_sessions.drop(['session_id'], axis=1)

group_columns = ['event_id']
sort_columns = ['session_start', 'action_time']
n_steps = 222
train_x, valid_x = pre_processing_functions.end_padding_and_split_sessions(data_sessions, group_columns, sort_columns, n_steps)

train_x = train_x[:,:-1,:]
valid_x = valid_x[:,:-1,:]


object_columns = [col for col in data_sessions if col.startswith('action_object')]
data_sessions = data_sessions[['event_id', 'valid', 'session_start', 'action_time', *object_columns]]

group_columns = ['event_id']
sort_columns = ['session_start', 'action_time']
n_steps = 222
train_y, valid_y = pre_processing_functions.end_padding_and_split_sessions(data_sessions, group_columns, sort_columns, n_steps)

train_y = train_y[:,1:,:]
valid_y = valid_y[:,1:,:]


''' Model. '''
seed(42)
tf.random.set_seed(42)

epochs, batch_size, units, rate = 100, 32, 256, 0.2
n_timesteps, n_features, n_outputs = train_x.shape[1], train_x.shape[2], train_y.shape[2]
model = Sequential()
model.add(Masking(mask_value=0.0, input_shape=(n_timesteps,n_features)))
model.add(GRU(units, return_sequences=True))
model.add(Dropout(rate))
model.add(TimeDistributed(Dense(units, activation='relu')))
model.add(TimeDistributed(Dense(n_outputs, activation='softmax')))
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

es = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=5)
mc = ModelCheckpoint('model_GRU4REC_concat.h5', monitor='val_loss', mode='min', verbose=1, save_best_only=True)

history = model.fit(train_x, train_y, validation_data=(valid_x, valid_y), epochs=epochs, batch_size=batch_size, callbacks=[es, mc])

saved_model = load_model('model_GRU4REC_concat.h5')
eval_accuracy = saved_model.evaluate(valid_x, valid_y)[1]