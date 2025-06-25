// Test frontend CORS connection
// Run this in browser console at http://localhost:3001

async function testCORS() {
  console.log('Testing CORS from frontend...');
  
  try {
    const response = await fetch('http://localhost:8080/api/status', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      mode: 'cors'
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ CORS Success! Data:', data);
      return data;
    } else {
      console.error('❌ Response error:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('❌ CORS Error:', error.message);
  }
}

// Run the test
testCORS();