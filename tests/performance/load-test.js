import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');

// Test configuration
export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users
    { duration: '2m', target: 20 },   // Ramp up to 20 users
    { duration: '5m', target: 20 },   // Stay at 20 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
    http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
    errors: ['rate<0.1'],              // Custom error rate must be below 10%
  },
};

// Base URL configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

// Test data
const users = [
  { username: 'admin', password: 'admin123' },
  { username: 'student1', password: 'student123' },
  { username: 'teacher1', password: 'teacher123' },
];

export function setup() {
  // Setup phase - create test data if needed
  console.log('Starting performance tests...');
  console.log(`Base URL: ${BASE_URL}`);
}

export default function () {
  // Test scenarios
  let scenarios = [
    testHomePage,
    testApiEndpoints,
    testCourseSearch,
    testUserAuthentication,
    testAdminDashboard,
  ];

  // Randomly select a scenario
  let scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  sleep(1);
}

function testHomePage() {
  let response = http.get(`${BASE_URL}/`);
  
  let success = check(response, {
    'homepage status is 200': (r) => r.status === 200,
    'homepage response time < 1000ms': (r) => r.timings.duration < 1000,
    'homepage contains title': (r) => r.body.includes('InLearning'),
  });

  errorRate.add(!success);
}

function testApiEndpoints() {
  // Test Flask API health
  let flaskResponse = http.get(`${BASE_URL.replace('8080', '5000')}/health`);
  
  let flaskSuccess = check(flaskResponse, {
    'API health status is 200': (r) => r.status === 200,
    'API response time < 500ms': (r) => r.timings.duration < 500,
  });

  // Test Django API endpoints
  let djangoResponse = http.get(`${BASE_URL}/api/courses/`);
  
  let djangoSuccess = check(djangoResponse, {
    'Django API accessible': (r) => r.status === 200 || r.status === 401, // 401 is OK if auth required
    'Django API response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  errorRate.add(!(flaskSuccess && djangoSuccess));
}

function testCourseSearch() {
  // Test course search functionality
  let searchTerms = ['python', 'javascript', 'machine learning', 'web development'];
  let term = searchTerms[Math.floor(Math.random() * searchTerms.length)];
  
  let response = http.get(`${BASE_URL}/courses/?search=${term}`);
  
  let success = check(response, {
    'search status is 200': (r) => r.status === 200,
    'search response time < 2000ms': (r) => r.timings.duration < 2000,
    'search returns results': (r) => r.body.length > 1000,
  });

  errorRate.add(!success);
}

function testUserAuthentication() {
  let user = users[Math.floor(Math.random() * users.length)];
  
  // Get login page first
  let loginPage = http.get(`${BASE_URL}/login/`);
  
  let loginSuccess = check(loginPage, {
    'login page loads': (r) => r.status === 200,
  });

  if (loginSuccess) {
    // Extract CSRF token if needed
    let csrfToken = loginPage.body.match(/name="csrfmiddlewaretoken" value="([^"]+)"/);
    
    if (csrfToken) {
      // Attempt login
      let loginData = {
        username: user.username,
        password: user.password,
        csrfmiddlewaretoken: csrfToken[1],
      };

      let loginResponse = http.post(`${BASE_URL}/login/`, loginData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      let authSuccess = check(loginResponse, {
        'login attempt processed': (r) => r.status === 200 || r.status === 302,
        'login response time < 1500ms': (r) => r.timings.duration < 1500,
      });

      errorRate.add(!authSuccess);
    }
  }
}

function testAdminDashboard() {
  // Test admin dashboard endpoints (without authentication for load testing)
  let adminEndpoints = [
    '/admin-dashboard/',
    '/admin-dashboard/monitoring/',
    '/admin-dashboard/analytics-api/',
    '/admin-dashboard/system-health/',
  ];

  let endpoint = adminEndpoints[Math.floor(Math.random() * adminEndpoints.length)];
  let response = http.get(`${BASE_URL}${endpoint}`);
  
  let success = check(response, {
    'admin endpoint accessible': (r) => r.status === 200 || r.status === 302 || r.status === 401,
    'admin response time < 2000ms': (r) => r.timings.duration < 2000,
  });

  errorRate.add(!success);
}

export function teardown(data) {
  // Cleanup phase
  console.log('Performance tests completed');
}

// Helper function to generate random course data
function generateCourseData() {
  const subjects = ['Python', 'JavaScript', 'Machine Learning', 'Data Science', 'Web Development'];
  const levels = ['Beginner', 'Intermediate', 'Advanced'];
  
  return {
    title: `Course on ${subjects[Math.floor(Math.random() * subjects.length)]}`,
    level: levels[Math.floor(Math.random() * levels.length)],
    description: 'Auto-generated course for load testing',
  };
}

// Database stress test scenario
export function databaseStressTest() {
  // Test multiple database operations
  let responses = http.batch([
    ['GET', `${BASE_URL}/courses/`],
    ['GET', `${BASE_URL}/users/`],
    ['GET', `${BASE_URL}/admin-dashboard/analytics-api/`],
  ]);

  let success = check(responses, {
    'all database queries succeed': (responses) => responses.every(r => r.status === 200 || r.status === 401),
    'all queries under 3s': (responses) => responses.every(r => r.timings.duration < 3000),
  });

  errorRate.add(!success);
} 