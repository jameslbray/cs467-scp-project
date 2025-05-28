// EditProfilePage.tsx
import React, { useState } from "react";
import Login from "../components/Login";
import UserEdit from "../components/EditProfile";

const EditProfilePage: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));

  const handleLogin = (newToken: string) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
  };

  return (
    <div>
      <h2>Login</h2>
      <Login onLogin={handleLogin} />

      <hr style={{ margin: "2rem 0" }} />

      <h2>Edit User Profile</h2>
      {token ? (
        <UserEdit token={token} />
      ) : (
        <p>Please log in to edit your user profile.</p>
      )}
    </div>
  );
};

export default EditProfilePage;