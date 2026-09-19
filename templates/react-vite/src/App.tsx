import React from 'react';

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem', textAlign: 'center' }}>
      <h1>{"{{APPLICATION_NAME}}"}</h1>
      <p>Frontend application running on DevForge</p>
      <div style={{ display: 'inline-block', padding: '0.5rem 1rem', background: '#22c55e20', color: '#16a34a', borderRadius: '4px' }}>
        Status: Healthy
      </div>
    </div>
  );
}
