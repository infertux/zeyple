package main

import (
	"bytes"
	"encoding/hex"
	"io"
	"testing"

	"golang.org/x/crypto/openpgp"
)

func readerFromHex(s string) io.Reader {
	data, err := hex.DecodeString(s)
	if err != nil {
		panic("readerFromHex: bad input")
	}
	return bytes.NewBuffer(data)
}

func TestReadKeyRing(t *testing.T) {
	kring, err := openpgp.ReadKeyRing(readerFromHex("12AB"))
	if err != nil {
		t.Error(err)
		return
	}
	if len(kring) != 2 || uint32(kring[0].PrimaryKey.KeyId) != 0xC20C31BB || uint32(kring[1].PrimaryKey.KeyId) != 0x1E35246B {
		t.Errorf("bad keyring: %#v", kring)
	}
}
