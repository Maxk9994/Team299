using System;
using Microsoft.Data.Sqlite;


public class DatabaseManager
{
    private readonly string connectionString = "Data Source=calendar.db";

    public void InitializeDatabase()
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        string sql = @"
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            Email TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL
        );";

        using var command = new SqliteCommand(sql, connection);
        command.ExecuteNonQuery();
    }

    public bool UserExists(string username, string email)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        string query = @"SELECT COUNT(*)
                         FROM Users
                         WHERE Username = @username OR Email = @email";

        using var command = new SqliteCommand(query, connection);
        command.Parameters.AddWithValue("@username", username);
        command.Parameters.AddWithValue("@email", email);

        int count = Convert.ToInt32(command.ExecuteScalar());
        return count > 0;
    }

    public bool RegisterUser(string username, string email, string password)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        string passwordHash = PasswordHelper.HashPassword(password);

        string query = @"INSERT INTO Users (Username, Email, PasswordHash)
                         VALUES (@username, @email, @passwordHash)";

        using var command = new SqliteCommand(query, connection);
        command.Parameters.AddWithValue("@username", username);
        command.Parameters.AddWithValue("@email", email);
        command.Parameters.AddWithValue("@passwordHash", passwordHash);

        try
        {
            int rows = command.ExecuteNonQuery();
            return rows > 0;
        }
        catch
        {
            return false;
        }
    }

    public bool LoginUser(string username, string password)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        string passwordHash = PasswordHelper.HashPassword(password);

        string query = @"SELECT COUNT(*)
                         FROM Users
                         WHERE Username = @username AND PasswordHash = @passwordHash";

        using var command = new SqliteCommand(query, connection);
        command.Parameters.AddWithValue("@username", username);
        command.Parameters.AddWithValue("@passwordHash", passwordHash);

        int count = Convert.ToInt32(command.ExecuteScalar());
        return count > 0;
    }
}