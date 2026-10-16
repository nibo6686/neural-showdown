const Module=require('node:module');const load=Module._load;
Module._load=function(request,...args){if(String(request).includes('pokemon-showdown'))throw Error('native engine load prohibited');return load.call(this,request,...args);};
