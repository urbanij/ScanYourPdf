-- Created on Mon May 25 18:00:22 CEST 2020

-- @project     : 
-- @author(s)   : Francesco Urbani

-- @file        : 
-- @descritpion : 
-- @version     : 


CREATE TABLE IF NOT EXISTS users (
    chat_id                 int         PRIMARY KEY, 
    state                   text        DEFAULT NULL,
    options                 text        DEFAULT NULL,
    files_scanned           int         DEFAULT NULL,
    data_scanned            int         DEFAULT NULL

);

