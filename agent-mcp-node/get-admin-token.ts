#!/usr/bin/env tsx
// Get admin token from database or globals

import { getDbConnection } from './src/db/connection.js';
import { initializeAdminToken } from './src/core/auth.js';
import { globalState } from './src/core/globals.js';

async function getAdminToken() {
  console.log('🔑 Retrieving Admin Token...');
  
  try {
    // Try to get from globals first (if server is running)
    if (globalState.adminToken) {
      console.log(`✅ Admin Token from Globals: ${globalState.adminToken}`);
      return globalState.adminToken;
    }
    
    // Initialize if not in memory
    const token = initializeAdminToken();
    console.log(`✅ Admin Token: ${token}`);
    
    return token;
  } catch (error) {
    console.error('❌ Failed to get admin token:', error);
    process.exit(1);
  }
}

getAdminToken().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});