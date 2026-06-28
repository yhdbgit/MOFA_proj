import { useState } from "react";
import {
  Button,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState("http://localhost:8080");
  const [citizenId, setCitizenId] = useState("citizen-mobile-demo");
  const [countryCode, setCountryCode] = useState("JP");
  const [chatId, setChatId] = useState("");
  const [message, setMessage] = useState("여권을 분실했고 현지 경찰서에 있습니다.");
  const [log, setLog] = useState([]);

  function appendLog(title, data) {
    setLog((current) => [{ title, data, time: new Date().toLocaleTimeString() }, ...current]);
  }

  async function createChat() {
    const response = await fetch(`${apiBaseUrl}/api/chats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ citizenId, countryCode }),
    });
    const body = await response.json();
    setChatId(body.id || "");
    appendLog("Chat created", body);
  }

  async function sendMessage() {
    if (!chatId) {
      appendLog("Missing chatId", "Create a chat first.");
      return;
    }

    const response = await fetch(`${apiBaseUrl}/api/chats/${chatId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ senderType: "CITIZEN", content: message }),
    });
    appendLog("Message sent", await response.json());
  }

  async function loadChat() {
    if (!chatId) return;
    const response = await fetch(`${apiBaseUrl}/api/chats/${chatId}`);
    appendLog("Chat loaded", await response.json());
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>MOFA Citizen App Test</Text>

        <Text style={styles.label}>Spring Boot API URL</Text>
        <TextInput style={styles.input} value={apiBaseUrl} onChangeText={setApiBaseUrl} autoCapitalize="none" />

        <Text style={styles.label}>Citizen ID</Text>
        <TextInput style={styles.input} value={citizenId} onChangeText={setCitizenId} autoCapitalize="none" />

        <Text style={styles.label}>Country Code</Text>
        <TextInput style={styles.input} value={countryCode} onChangeText={setCountryCode} autoCapitalize="characters" />

        <View style={styles.buttonGroup}>
          <Button title="Create Chat" onPress={createChat} />
        </View>

        <Text style={styles.label}>Chat ID</Text>
        <TextInput style={styles.input} value={chatId} onChangeText={setChatId} autoCapitalize="none" />

        <Text style={styles.label}>Message</Text>
        <TextInput
          style={[styles.input, styles.messageInput]}
          value={message}
          onChangeText={setMessage}
          multiline
        />

        <View style={styles.buttonGroup}>
          <Button title="Send Message" onPress={sendMessage} />
        </View>
        <View style={styles.buttonGroup}>
          <Button title="Load Chat" onPress={loadChat} />
        </View>

        {log.map((entry, index) => (
          <View style={styles.card} key={`${entry.time}-${index}`}>
            <Text style={styles.cardTitle}>{entry.title}</Text>
            <Text style={styles.time}>{entry.time}</Text>
            <Text style={styles.mono}>{JSON.stringify(entry.data, null, 2)}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#f4f6f8",
  },
  container: {
    padding: 20,
  },
  title: {
    color: "#1f2933",
    fontSize: 24,
    fontWeight: "700",
    marginBottom: 16,
  },
  label: {
    color: "#52616f",
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 6,
    marginTop: 10,
  },
  input: {
    backgroundColor: "white",
    borderColor: "#c7d0da",
    borderRadius: 6,
    borderWidth: 1,
    padding: 10,
  },
  messageInput: {
    minHeight: 80,
    textAlignVertical: "top",
  },
  buttonGroup: {
    marginTop: 12,
  },
  card: {
    backgroundColor: "white",
    borderColor: "#d9e1e8",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 14,
    padding: 12,
  },
  cardTitle: {
    fontWeight: "700",
  },
  time: {
    color: "#6b7886",
    marginBottom: 8,
    marginTop: 2,
  },
  mono: {
    fontFamily: "Courier",
    fontSize: 12,
  },
});
