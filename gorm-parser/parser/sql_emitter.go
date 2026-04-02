package parser

import "encoding/json"

type output struct {
	Chains []GORMChain `json:"chains"`
}

func EmitJSON(chains []GORMChain) (string, error) {
	output := output{
		Chains: chains,
	}

	jsonBytes, err := json.MarshalIndent(output, "", "  ")
	if err != nil {
		return "", err
	}

	return string(jsonBytes), nil
}