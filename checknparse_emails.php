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

date_default_timezone_set("Africa/Johannesburg");

// Error log file
$logFile = 'newersabga_cron_log.txt'; // Adjust this path as needed

function log_debug($message) {
    global $logFile;
    $timestamp = date("Y-m-d H:i:s");
    $logMessage = "[$timestamp] $message\n";
    echo $logMessage;
    file_put_contents($logFile, $logMessage, FILE_APPEND);
}

// Create a single database connection
$conn = new mysqli($host, $db_user, $db_password, $dbname);
if ($conn->connect_error) {
    log_debug("Database connection error: " . $conn->connect_error);
    exit;
}

// Fetch MatchTypeID by identifier
function get_match_type_id_by_identifier($conn, $identifier) {
    log_debug("Searching for MatchTypeID with Identifier: $identifier");
    $stmt = $conn->prepare("SELECT MatchTypeID FROM MatchType WHERE Identifier = ?");
    $stmt->bind_param("s", $identifier);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        log_debug("Found MatchTypeID: " . $row['MatchTypeID']);
        return $row['MatchTypeID'];
    } else {
        log_debug("No MatchTypeID found for identifier '$identifier'");
        return null;
    }
}

// Fetch PlayerID by nickname
function get_player_id_by_nickname($conn, $nickname) {
    log_debug("Searching for PlayerID with Nickname: $nickname");
    $stmt = $conn->prepare("SELECT PlayerID FROM Players WHERE Nickname = ?");
    $stmt->bind_param("s", $nickname);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        log_debug("Found PlayerID: " . $row['PlayerID'] . " for Nickname: $nickname");
        return $row['PlayerID'];
    } else {
        log_debug("No PlayerID found for Nickname: $nickname");
        return null;
    }
}

// Fetch Fixture by MatchTypeID and PlayerIDs
function get_fixture($conn, $match_type_id, $player1_id, $player2_id) {
    log_debug("Searching for fixture with MatchTypeID = $match_type_id, Player1ID = $player1_id, Player2ID = $player2_id");
    $stmt = $conn->prepare("
        SELECT FixtureID, Completed
        FROM Fixtures
        WHERE MatchTypeID = ? AND 
              ((Player1ID = ? AND Player2ID = ?) OR (Player1ID = ? AND Player2ID = ?))
    ");
    $stmt->bind_param("iiiii", $match_type_id, $player1_id, $player2_id, $player2_id, $player1_id);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        log_debug("Found Fixture: " . json_encode($row));
        return $row;
    } else {
        log_debug("No matching fixture found");
        return null;
    }
}

// Insert match results into the database
function insert_match_result($conn, $fixture_id, $player1_points, $player1_pr, $player1_luck, 
                             $player2_points, $player2_pr, $player2_luck, $match_type_id, $player1_id, $player2_id) {
    log_debug("Inserting match result for FixtureID = $fixture_id");
    $stmt = $conn->prepare("
        INSERT INTO MatchResults (FixtureID, Player1Points, Player1PR, Player1Luck, 
                                  Player2Points, Player2PR, Player2Luck, MatchTypeID, 
                                  Player1ID, Player2ID, Date, TimeCompleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
    ");
    $stmt->bind_param("iiddiddiii", $fixture_id, $player1_points, $player1_pr, $player1_luck, 
                                       $player2_points, $player2_pr, $player2_luck, $match_type_id, 
                                       $player1_id, $player2_id);
    $stmt->execute();

    if ($stmt->affected_rows > 0) {
        log_debug("Match result added successfully");
        return true;
    } else {
        log_debug("Failed to insert match result for FixtureID = $fixture_id");
        return false;
    }
}

// Main email processing logic
try {
    $inbox = imap_open("{{$email_host}:$email_port/imap/ssl}INBOX", $email_user, $email_password);
    if (!$inbox) {
        throw new Exception("Cannot connect to email server: " . imap_last_error());
    }

   // Loop to check emails every 5 minutes within the 2-hour cron job
    $end_time = time() + (2 * 60 * 60); // 2 hours from the start
    while (time() < $end_time) {
 
    // Process emails
    $emails = imap_search($inbox, 'UNSEEN SUBJECT "Admin: A league match was played"');
    $timestamp = date("Y-m-d H:i:s");
    log_debug("At $timestamp - unseen emails checked");

    if ($emails) {
        log_debug("Found " . count($emails) . " unseen email(s) matching the subject");

        foreach ($emails as $email_id) {
            $match_type_id = null;
            $player1_id = null;
            $player2_id = null;
            $fixture = null;

            $msg = imap_fetchbody($inbox, $email_id, 1);
            $subject = imap_headerinfo($inbox, $email_id)->subject;
            $email_header = imap_headerinfo($inbox, $email_id);
            
            // Extract the 'To:' field (recipient)
            $to_field = $email_header->to[0]->mailbox . '@' . $email_header->to[0]->host;

            // Log the subject and the recipient
            log_debug("Original email subject: $subject");
            $cleaned_subject = preg_replace('/^(Fwd:|Re:)\s*/', '', $subject);
            log_debug("Cleaned email subject: $cleaned_subject");
            log_debug("Email recipient: $to_field");
                
            // First try extract matchidentifier from the "To" address
            if (!empty($email_header->to)) {
                $to_field = $email_header->to[0]->mailbox . '@' . $email_header->to[0]->host;
            
                // Extract the identifier from the To address
                if (preg_match('/\+([a-zA-Z0-9_-]+)@/', $to_field, $matches)) {
                    $sort_part = $matches[1];  // Extracted part after '+' (e.g., 'sort4')
                    log_debug("Extracted identifier from To address: $sort_part");
                    $identifier = $sort_part;
                } else {
                    log_debug("No identifier found in To address: $to_field");
            
                    // Extract match type identifier from Fwd field
                    preg_match('/To:.*<(.+?)>/', $msg, $forwarded_to);
                    if ($forwarded_to) {
                        $forwarded_email = $forwarded_to[1];
                        log_debug("Forwarded email address found: $forwarded_email");
            
                        preg_match('/\+([^@]+)@/', $forwarded_email, $match_type_identifier);
                        if ($match_type_identifier) {
                            $identifier = $match_type_identifier[1];
                            log_debug("Match type identifier extracted: $identifier");
                        } else {
                            log_debug("No match type identifier in Fwd part either.");
                            continue; // Skip this email
                        }
                    } else {
                        log_debug("No forwarded email address found.");
                        continue; // Skip this email
                    }
                }
            } else {
                log_debug("No To address found.");
            }
            
             $match_type_id = get_match_type_id_by_identifier($conn, $identifier);
             if (!$match_type_id) {
                log_debug("Failed to retrieve MatchTypeID for identifier: $identifier");
                continue; // Skip this email
            } else {
                log_debug("No forwarded email address found.");
            }

            // Extract player nicknames and match data
            preg_match('/between ([\w\s]+) \((\d+ \d+ [\d.]+ [\-\d.]+)\) and ([\w\s]+) \((\d+ \d+ [\d.]+ [\-\d.]+)\)/', $cleaned_subject, $match);
            if ($match) {
                log_debug("Extracted match details: " . json_encode($match));

                $player1_id = get_player_id_by_nickname($conn, $match[1]);
                $player2_id = get_player_id_by_nickname($conn, $match[3]);

                if (!$player1_id || !$player2_id) {
                    log_debug("Failed to find PlayerIDs for players: $match[1], $match[3]");
                    continue; // Skip this email
                }

                list($p1_points, $p1_length, $p1_pr, $p1_luck) = explode(' ', $match[2]);
                list($p2_points, $p2_length, $p2_pr, $p2_luck) = explode(' ', $match[4]);

                log_debug("Parsed player stats - Player1: [$p1_points, $p1_length, $p1_pr, $p1_luck], Player2: [$p2_points, $p2_length, $p2_pr, $p2_luck]");

        // Find the matching fixture
        $fixture = get_fixture($conn, $match_type_id, $player1_id, $player2_id);
        if ($fixture) {
            log_debug("Fixture found: " . json_encode($fixture));
            if ($fixture['Completed'] == 0) {
                $success = insert_match_result($conn, $fixture['FixtureID'], min($p1_points, $p1_length), (float)$p1_pr, (float)$p1_luck,
                                               min($p2_points, $p2_length), (float)$p2_pr, (float)$p2_luck, $match_type_id, $player1_id, $player2_id);
                if ($success) {
                    $update_stmt = $conn->prepare("UPDATE Fixtures SET Completed = 1 WHERE FixtureID = ?");
                    $update_stmt->bind_param("i", $fixture['FixtureID']);
                    $update_stmt->execute();
                    log_debug("Fixture marked as completed");
                }
            } else {
                log_debug("Fixture already completed. Skipping.");
            }
        } else {
            log_debug("No matching fixture found for MatchTypeID: $match_type_id, Player1ID: $player1_id, Player2ID: $player2_id");
        }
    } else {
        log_debug("No match details for extraction.")
      } 
      
      } else {
        log_debug("No new emails found.");
    }
       // Sleep for 5 minutes before checking again
        sleep(300); // 5 minutes
    }

    imap_close($inbox);
} catch (Exception $e) {
    log_debug("Error: " . $e->getMessage());
}
?>
