package com.iriusrisk.cli.commands;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.File;
import java.io.IOException;

public class IriusMapper {

    private static IriusMapper INSTANCE;
    private static final ObjectMapper MAPPER = initialize();

    private static ObjectMapper initialize() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.enable(SerializationFeature.INDENT_OUTPUT);
        return mapper;
    }

    public static IriusMapper getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new IriusMapper();
        }
        return INSTANCE;
    }

    public <T> T readValue(File file, Class<T> clazz) throws IOException {
        return MAPPER.readValue(file, clazz);
    }

    public void writeValue(File file, Object value) throws IOException {
        MAPPER.writeValue(file, value);
    }

    public String writeValueAsString(Object value) throws JsonProcessingException {
        return MAPPER.writeValueAsString(value);
    }
}
