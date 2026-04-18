CREATE TABLE Users (
    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
    Username TEXT NOT NULL UNIQUE,
    Email TEXT NOT NULL,
    Password TEXT NOT NULL
);

CREATE TABLE Calendars (
    CalendarID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    OwnerID INTEGER,
    FOREIGN KEY (OwnerID) REFERENCES Users(UserID)
);

CREATE TABLE Events (
    EventID INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT NOT NULL,
    Description TEXT,
    StartTime DATETIME,
    EndTime DATETIME,
    CalendarID INTEGER,
    CreatedBy INTEGER,
    FOREIGN KEY (CalendarID) REFERENCES Calendars(CalendarID),
    FOREIGN KEY (CreatedBy) REFERENCES Users(UserID)
);

CREATE TABLE EventParticipants (
    EventID INTEGER,
    UserID INTEGER,
    Role TEXT,
    PRIMARY KEY (EventID, UserID),
    FOREIGN KEY (EventID) REFERENCES Events(EventID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);