import { combineReducers } from 'redux';
import { configureStore } from '@reduxjs/toolkit';
import storage from 'redux-persist/lib/storage';
import { persistReducer, persistStore } from 'redux-persist';
import { checkAndUpdateSchema } from './schema';

const persistConfig = {
    key: 'root',
    storage,
};

const rootReducer = combineReducers({
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
    reducer: persistedReducer
});

const initialSchema = {
  };

checkAndUpdateSchema(initialSchema, store);

export const persistor = persistStore(store);