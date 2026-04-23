import { persistStore } from 'redux-persist';

export function checkAndUpdateSchema(initialSchema, store) {
    const keysSchema = extractKeys(initialSchema);
    const initialSchemaHash = generateHash(keysSchema);
    const persistedSchemaHash = localStorage.getItem('schemaHash');


    if (initialSchemaHash != persistedSchemaHash) {
        setTimeout(() => {
            persistStore(store).purge();  // uncomment this if you want to reset the state
        }, 0);
        localStorage.setItem('schemaHash', initialSchemaHash);
    }
}

function generateHash(object) {
    const str = JSON.stringify(object);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
}

function extractKeys(obj) {
    const keysObj = Array.isArray(obj) ? [] : {};
    for (const key in obj) {
        if (typeof obj[key] === 'object' && obj[key] !== null) {
            keysObj[key] = extractKeys(obj[key]);
        } else {
            keysObj[key] = true;
        }
    }
    return keysObj;
}
