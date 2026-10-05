package example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SupportDesk {
    public static void main(String[] args) {
        // HttpURLConnection must never replay a generation POST after a connection failure.
        System.setProperty("sun.net.http.retryPost", "false");
        SpringApplication.run(SupportDesk.class, args);
    }
}
