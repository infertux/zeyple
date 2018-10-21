// Copyright 2012-2018 Cédric Félizard

package main

import (
	"bytes"
	// "compress/gzip"
	"crypto"
	"fmt"
	"os"
	"runtime"

	"golang.org/x/crypto/openpgp"
	"golang.org/x/crypto/openpgp/armor"
	"golang.org/x/crypto/openpgp/packet"
)

// var cfg *config

func main() {
	// Use all processor cores.
	runtime.GOMAXPROCS(runtime.NumCPU())

	// Work around defer not working after os.Exit()
	if err := zeypleMain(); err != nil {
		os.Exit(1)
	}
}

func zeypleMain() error {
	//config, err := loadConfig("./zeyple.conf", "/etc/zeyple.conf")

	// CLI:
	// zeyple --help
	// zeyple enable|disable # calls `postconf ...`
	// zeyple key --list
	//            --import email@example.net
	//            --delete email@example.net
	// zeyple encrypt recipient1@example.net recipient2@foo.bar < message
	//

	entityConfig := &packet.Config{
		DefaultHash: crypto.SHA256,
	}

	entity, err := openpgp.NewEntity("name", "comment", "email@example.net", entityConfig)
	if err != nil {
		fmt.Printf("%v", err)
	}

	encrypted, err := encrypt(entity, []byte("foo"))
	if err != nil {
		fmt.Printf("%v", err)
	}

	fmt.Printf("%v", encrypted)

	return nil
}

func encrypt(entity *openpgp.Entity, message []byte) ([]byte, error) {
	buf := new(bytes.Buffer)

	encoderWriter, err := armor.Encode(buf, string(message[:]), make(map[string]string))
	if err != nil {
		return []byte{}, fmt.Errorf("Error creating OpenPGP armor: %v", err)
	}

	encryptorWriter, err := openpgp.Encrypt(encoderWriter, []*openpgp.Entity{entity}, nil, nil, nil)
	if err != nil {
		return []byte{}, fmt.Errorf("Error creating entity for encryption: %v", err)
	}

	//compressorWriter, err := gzip.NewWriterLevel(encryptorWriter, gzip.BestCompression)
	//if err != nil {
	//	return []byte{}, fmt.Errorf("Invalid compression level: %v", err)
	//}

	//messageReader := bytes.NewReader(message)
	//_, err = io.Copy(encryptorWriter, messageReader)
	//if err != nil {
	//	return []byte{}, fmt.Errorf("Error writing data to compressor: %v", err)
	//}

	//compressorWriter.Close()
	encryptorWriter.Close()
	encoderWriter.Close()

	return buf.Bytes(), nil
}
