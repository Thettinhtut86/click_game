INSERT INTO players
(
    user_id,
    user_name,
    color
)
VALUES
(
    '1',
    'player1',
    'red'
),
(
    '2',
    'player2',
    'blue'
);



INSERT INTO rooms
(
    room_id,
    room_name,
    host_id,
    option_type,
    status
)
VALUES
(
    'room1',
    'Test Room',
    '1',
    'asc',
    'waiting'
);



INSERT INTO chat
(
    room_id,
    user_id,
    message
)
VALUES
(
    'room1',
    '1',
    'Hello'
);