const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { Pool } = require('pg');

// Database connection properties (Values replaced with ? on GitHub. Change to actual values when running local. )
const pool = new Pool({
  user: '?',  
  host: '?',  // IP of server
  database: '?',  
  password: '?',  
  port: 5432,    
});

// Express and Socket.IO setup
const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',  // Enable React App to connect.
  },
});

io.on('connection', (socket) => {
  console.log('New client connected:', socket.id);

  socket.on('join_room', (room) => {
    socket.join(room);
    console.log(`Client ${socket.id} joined room ${room}`);
  });

  socket.on('send_message', async (data) => {
    const { user, text, room, timestamp } = data;

    // Save message to PostgreSQL database.
    try {
      await pool.query(
        'INSERT INTO chat_messages (user_name, text, room, timestamp) VALUES ($1, $2, $3, $4)',
        [user, text, room, timestamp]
      );

      // Broadcast message to all users. 
      io.to(room).emit('chat_message', data);
    } catch (err) {
      console.error('DB insert error:', err);
    }
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});

server.listen(3001, () => {
  console.log('http://localhost:3001');
});
