# SycoLibre Chat Frontend

A modern, secure chat application built with React, TypeScript, and Tailwind CSS.

## Features

- **Authentication System**: JWT-based authentication with token revocation
- **Real-time Chat**: Powered by Socket.io
- **User Status**: Track online/offline status of users
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Works on desktop and mobile devices

## Authentication Flow

The application uses JWT (JSON Web Tokens) for authentication:

1. **Login/Registration**: Users authenticate with username/password
2. **Token Storage**: JWT is stored in localStorage and used for API requests
3. **Token Validation**: Tokens are validated on each protected route access
4. **Token Revocation**: Tokens are revoked on logout

## API Endpoints

The frontend communicates with the following API endpoints:

- `POST /api/auth/login`: Authenticate user and receive JWT
- `POST /api/auth/register`: Register a new user
- `GET /api/auth/validate`: Validate JWT and get user data
- `POST /api/auth/logout`: Revoke JWT
- `GET /api/users/profile`: Get user profile
- `PUT /api/users/profile`: Update user profile

## Socket.io Events

The application uses Socket.io for real-time communication:

- `presence:request_friend_statuses`: Request status of all friends
- `presence:friend_statuses`: Receive status of all friends
- `presence:friend_status_changed`: Notification when a friend's status changes
- `presence:update_status`: Update current user's status

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   # or
   yarn
   ```

3. Start the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. Open [http://localhost:5173](http://localhost:5173) in your browser

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── assets/          # Images, fonts, etc.
│   ├── components/      # Reusable UI components
│   ├── contexts/        # React contexts (theme, auth)
│   ├── pages/           # Page components
│   ├── services/        # API services
│   ├── socket/          # Socket.io event handlers
│   ├── types/           # TypeScript type definitions
│   ├── App.tsx          # Main application component
│   └── main.tsx         # Application entry point
├── index.html           # HTML template
├── package.json         # Dependencies and scripts
├── tailwind.config.ts   # Tailwind CSS configuration
└── tsconfig.json        # TypeScript configuration
```

## Development

### Adding New Features

1. Create new components in the `src/components` directory
2. Add new pages in the `src/pages` directory
3. Update routes in `App.tsx`
4. Add new API endpoints in `src/services/api.ts`
5. Add new Socket.io events in `src/socket/events.ts`

### Styling

The application uses Tailwind CSS for styling. Custom styles can be added in `src/index.css`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
