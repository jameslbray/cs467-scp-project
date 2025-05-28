import React, { useState, useEffect, FormEvent } from "react";
import axios from "axios";

const API_BASE_URL = "http://localhost:8001";

interface User {
  email: string;
  profile_picture_url: string;
}

interface UserEditProps {
  token: string;
}

const EditProfile: React.FC<UserEditProps> = ({ token }) => {
  const [email, setEmail] = useState<string>("");
  const [profile_picture_url, setprofile_picture_url] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    axios
      .get<User>(`${API_BASE_URL}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      .then((res) => {
        setEmail(res.data.email ?? "");
        setprofile_picture_url(res.data.profile_picture_url ?? "");
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load user data", err);
        setLoading(false);
      });
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    try {
      await axios.put(
        `${API_BASE_URL}/users/me`,
        { email, profile_picture_url }, 
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      alert("User updated!");
    } catch (err) {
      console.error("Failed to update user", err);
      alert("Failed to update user");
    }
  };

  if (loading) return <p>Loading user data...</p>;

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="email">Email:</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>

      <div>
        <label htmlFor="profile_picture_url">profile_picture_url:</label>
        <input
          id="profile_picture_url"
          type="text" 
          value={profile_picture_url}
          onChange={(e) => setprofile_picture_url(e.target.value)}
          required
        />
      </div>

      <button type="submit">Update Profile</button>
    </form>
  );
};

export default EditProfile;
