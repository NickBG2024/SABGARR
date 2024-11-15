<?php
// Email server and database credentials
$host = 'sql58.jnb2.host-h.net';
$db_user = 'sabga_admin';
$db_password = '6f5f73102v7Y1A';
$dbname = 'sabga_test';

$email_host = 'mail.sabga.co.za';
$email_user = 'matchresults@sabga.co.za';
$email_password = 'EvieTessa2021!';
$email_port = 993;

// Error log file
$logFile = 'email_cron_error_log.txt';

// Create a single database connection
$conn = new mysqli($host, $db_user, $db_password, $dbname);
if ($conn->connect_error) {
    log_error("Database connection error: " . $conn->connect_error);
    exit;
}

function log_error($errorMessage) {
    global $logFile;
    $timestamp = date("Y-m-d H:i:s");
    file_put_contents($logFile, "[$timestamp] $errorMessage\n", FILE_APPEND);
}

function get_match_type_id_by_identifier($conn, $identifier) {
    $stmt = $conn->prepare("SELECT MatchTypeID FROM MatchType WHERE Identifier = ?");
    $stmt->bind_param("s", $identifier);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        return $row['MatchTypeID'];
    } else {
        log_error("No MatchTypeID found for identifier '$identifier'");
        echo "No MatchTypeID found for identifier\n";
        return null;
    }
}

function get_player_id_by_nickname($conn, $nickname) {
    $stmt = $conn->prepare("SELECT PlayerID FROM Players WHERE Nickname = ?");
    $stmt->bind_param("s", $nickname);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        return $row['PlayerID'];
    } else {
        log_error("No PlayerID found for nickname '$nickname'");
        echo "No PlayerID found for nickname\n";
        return null;
    }
}

function get_fixture($conn, $match_type_id, $player1_id, $player2_id) {
    $stmt = $conn->prepare('
        SELECT FixtureID, Completed
        FROM Fixtures
        WHERE MatchTypeID = ? AND 
              ((Player1ID = ? AND Player2ID = ?) OR (Player1ID = ? AND Player2ID = ?))
    ');
    $stmt->bind_param("iiiii", $match_type_id, $player1_id, $player2_id, $player2_id, $player1_id);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        return $row;
    } else {
        log_error("No matching fixture found for MatchTypeID = $match_type_id, Player1ID = $player1_id, Player2ID = $player2_id");
        echo "No matching fixture found for MatchTypeID\n";
        return null;
    }
}

function insert_match_result($conn, $fixture_id, $player1_points, $player1_pr, $player1_luck, 
                             $player2_points, $player2_pr, $player2_luck, $match_type_id, $player1_id, $player2_id) {
    $stmt = $conn->prepare("
        INSERT INTO MatchResults (FixtureID, Player1Points, Player1PR, Player1Luck, 
                                  Player2Points, Player2PR, Player2Luck, MatchTypeID, 
                                  Player1ID, Player2ID, Date, TimeCompleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
    ");
    $stmt->bind_param("iiiiiddddi", $fixture_id, $player1_points, $player1_pr, $player1_luck, 
                                        $player2_points, $player2_pr, $player2_luck, $match_type_id, 
                                        $player1_id, $player2_id);
    $stmt->execute();

    if ($stmt->affected_rows > 0) {
        return true;
    } else {
        log_error("Failed to insert match result for FixtureID = $fixture_id");
        echo "Failed to insert match result successfully\n";
        return false;
    }
}

// Main code to connect to email server and process emails
try {
    $inbox = imap_open("{{$email_host}:$email_port/imap/ssl}INBOX", $email_user, $email_password);
    if (!$inbox) {
        throw new Exception("Cannot connect to email server: " . imap_last_error());
    }

    // Loop to check emails every 5 minutes
   // while (true) {
        // Search for UNSEEN emails with the specified subject
        $emails = imap_search($inbox, 'UNSEEN SUBJECT "Admin: A league match was played"');
        echo "Checking for unseen emails with subject: 'Admin: A league match was played'...\n";
        
        if ($emails) {
            echo "Found " . count($emails) . " unseen email(s) matching the subject.\n";
        
            foreach ($emails as $email_id) {
                // Fetch the body of the email
                $msg = imap_fetchbody($inbox, $email_id, 1);
        
                // Get the subject of the email
                $subject = imap_headerinfo($inbox, $email_id)->subject;
                echo "Original email subject: $subject\n";
        
                // Clean the subject by removing "Fwd:" or "Re:" prefixes
                $cleaned_subject = preg_replace('/^(Fwd:|Re:)\s*/', '', $subject);
                echo "Cleaned email subject: $cleaned_subject\n";
        
                // Look for the forwarded-to email address in the body
                preg_match('/To:.*<(.+?)>/', $msg, $forwarded_to);
                if ($forwarded_to) {
                    $forwarded_email = $forwarded_to[1];
                    echo "Forwarded email address found: $forwarded_email\n";
        
                    // Extract the match type identifier from the forwarded email
                    preg_match('/\+([^@]+)@/', $forwarded_email, $match_type_identifier);
                    if ($match_type_identifier) {
                        echo "Match type identifier extracted: " . $match_type_identifier[1] . "\n";
                        $match_type_id = get_match_type_id_by_identifier($conn, $match_type_identifier[1]);
                        if (!$match_type_id) continue;
                    }
                }

                preg_match('/between (\w+) \(([^)]+)\) and (\w+) \(([^)]+)\)/', $cleaned_subject, $match);
                if ($match) {
                    $player1_id = get_player_id_by_nickname($conn, $match[1]);
                    $player2_id = get_player_id_by_nickname($conn, $match[3]);

                    list($p1_points, $p1_length, $p1_pr, $p1_luck) = explode(' ', $match[2]);
                    list($p2_points, $p2_length, $p2_pr, $p2_luck) = explode(' ', $match[4]);

                    // Ensure PR and Luck are floats
                    $p1_pr = (float)$p1_pr;
                    $p1_luck = (float)$p1_luck;
                    $p2_pr = (float)$p2_pr;
                    $p2_luck = (float)$p2_luck;

                    $fixture = get_fixture($conn, $match_type_id, $player1_id, $player2_id);
                    if ($fixture && $fixture['Completed'] == 0) {
                        if (insert_match_result($conn, $fixture['FixtureID'], min($p1_points, $p1_length), $p1_pr, $p1_luck, 
                                               min($p2_points, $p2_length), $p2_pr, $p2_luck, $match_type_id, $player1_id, $player2_id)) {
                            echo "Match result added successfully!\n";
                            $update_stmt = $conn->prepare("UPDATE Fixtures SET Completed = 1 WHERE FixtureID = ?");
                            $update_stmt->bind_param("i", $fixture['FixtureID']);
                            $update_stmt->execute();
                        } else {
                            echo "Failed to add match result.\n";
                        }
                    }
                } else {
                    log_error("No match data found in subject: $subject");
                    echo "No match data found in subject: $subject";
                }
            }
        } else {
            log_error("No unseen emails found with the specified subject.");
            echo "No unseen emails found.\n";
        }

        // Wait for 5 minutes before checking for new emails
        //sleep(5 * 60);
    //}

    imap_close($inbox);
    echo "closing inbox";
} catch (Exception $e) {
    log_error("Error: " . $e->getMessage());
}

// Close the database connection at the end
$conn->close();
?>
